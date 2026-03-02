# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Worker agent: read-modify-write using file_reader, file_writer, repo_search."""

import logging
import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

from ..models import ArtifactMetadata, TaskState
from ..prompt_templates import get_worker_system_prompt, get_worker_user_prompt
from ..reliability.rollback import save_backup
from ..structured_output_schema import CodeEditOutput
from ..tools import (
    ListFilesInput,
    ReadFileInput,
    SearchCodeInput,
    WriteFileInput,
)

log = logging.getLogger(__name__)


class WorkerStepConfig(FunctionBaseConfig, name="worker_step"):
    """Configuration for the Worker step."""

    llm_name: LLMRef = Field(
        description="LLM to use for code generation (read file -> generate/edit content -> apply).",
    )
    description: str = Field(
        default="Read files, call LLM to generate or edit code, apply via write_file, update TaskState artifacts.",
        description="Description of the worker step",
    )


def _get_tool(builder: Builder, preferred: str, fallback: str):
    """Resolve tool by preferred name with fallback (e.g. file_reader then read_file)."""
    try:
        return builder.get_function(preferred)
    except Exception:
        try:
            return builder.get_function(fallback)
        except Exception:
            return None


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```lang ... ```) and return only the code."""
    if not text or not isinstance(text, str):
        return text or ""
    t = text.strip()
    # Match ```optional_lang\ncontent\n```
    m = re.search(r"^```[\w]*\s*\n?(.*?)```\s*$", t, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Try to strip single opening fence only (incomplete response)
    if t.startswith("```"):
        t = re.sub(r"^```[\w]*\s*\n?", "", t)
        if t.endswith("```"):
            t = t[: t.rfind("```")].rstrip()
        return t.strip()
    return t


@register_function(config_type=WorkerStepConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def worker_step(config: WorkerStepConfig, builder: Builder):
    """Worker step: tool-grounded read-modify-write using file_reader, file_writer, repo_search."""

    log.info("Initializing worker_step (file_reader / file_writer / repo_search)")

    file_reader_fn = _get_tool(builder, "file_reader", "read_file")
    file_writer_fn = _get_tool(builder, "file_writer", "write_file")
    repo_search_fn = _get_tool(builder, "repo_search", "search_code")
    code_gen_fn = None
    try:
        code_gen_fn = builder.get_function("code_generation_tool")
    except Exception:
        log.debug("Worker: code_generation_tool not available, using LLM only")
    try:
        list_files_fn = builder.get_function("list_files")
    except Exception:
        list_files_fn = None

    if not file_reader_fn or not file_writer_fn:
        raise RuntimeError(
            "Worker requires at least one of (file_reader, read_file) and one of (file_writer, write_file)."
        )

    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    structured_llm = llm.with_structured_output(CodeEditOutput)

    async def _worker(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        current = state.get_current_subtask()
        if not current:
            log.info("Worker: no current subtask, skipping")
            return state

        # Reliability: limit retries per subtask
        retry_count = state.subtask_retry_count.get(current.id, 0)
        if retry_count > state.max_retries_per_subtask:
            log.warning("Worker: subtask %s over retry limit (%s), marking blocked", current.id, state.max_retries_per_subtask)
            subtask_idx = state.current_subtask_index
            new_subtasks = list(state.subtasks)
            if subtask_idx is not None and subtask_idx < len(new_subtasks):
                new_subtasks[subtask_idx] = new_subtasks[subtask_idx].model_copy(update={"status": "blocked"})
            state.subtasks = new_subtasks
            state.updated_at = datetime.now().isoformat()
            return state

        subtask_idx = state.current_subtask_index
        new_subtasks = list(state.subtasks)
        if subtask_idx is not None and subtask_idx < len(new_subtasks):
            new_subtasks[subtask_idx] = new_subtasks[subtask_idx].model_copy(
                update={"status": "in_progress"}
            )
        state.subtasks = new_subtasks

        repo_root = state.repo_root or "."
        repo_path = Path(repo_root).resolve()
        # When output_dir is set, all LLM-generated files go under repo_root/output_dir
        output_dir_str = (state.output_dir and str(state.output_dir).strip()) or None
        if output_dir_str:
            artifacts_base = (repo_path / output_dir_str).resolve()
            artifacts_base.mkdir(parents=True, exist_ok=True)
        else:
            artifacts_base = repo_path

        def _strip_output_prefix(path: str) -> str:
            """Strip output_dir prefix so 'output/index.html' -> 'index.html' (avoids output/output/...)."""
            if not path or not output_dir_str:
                return path.strip() if path else ""
            p = path.strip().replace("\\", "/")
            prefix = output_dir_str.replace("\\", "/").rstrip("/")
            if prefix and (p.startswith(prefix + "/") or p == prefix):
                return p[len(prefix) :].lstrip("/") if p != prefix else ""
            return p

        artifacts = dict(state.artifacts)
        now = datetime.now().isoformat()

        file_context_parts = []
        paths_to_edit = list(current.target_files) if current.target_files else []

        if not paths_to_edit and list_files_fn:
            try:
                listing = await list_files_fn.ainvoke(
                    ListFilesInput(directory=str(artifacts_base), recursive=False)
                )
                file_context_parts.append(f"Repository listing:\n{listing or ''}")
            except Exception as e:
                log.debug("Worker: list_files failed: %s", e)

        for rel_path in paths_to_edit:
            if not rel_path or not rel_path.strip():
                continue
            rel_normalized = _strip_output_prefix(rel_path)
            if not rel_normalized:
                continue
            abs_path = (artifacts_base / rel_normalized).resolve()
            try:
                # Use a plain dict so this works with either `file_reader` (nat.tool.file_reader)
                # or plugin `read_file` without Pydantic model class mismatch.
                out = await file_reader_fn.ainvoke(
                    {"file_path": str(abs_path), "encoding": "utf-8", "max_size_mb": 10}
                )
                file_context_parts.append(f"--- File: {rel_normalized} ---\n{out}")
            except Exception as e:
                file_context_parts.append(f"--- File: {rel_normalized} (read error: {e}) ---\n(create or fix this file)")

        file_context = "\n\n".join(file_context_parts) if file_context_parts else "(no files read; suggest a new file path and content.)"

        search_context = ""
        if repo_search_fn:
            try:
                pattern = "def |class "
                if current.description:
                    words = [w.strip(".,") for w in current.description.split() if len(w) > 2][:5]
                    if words:
                        pattern = "|".join(words[:3])
                search_out = await repo_search_fn.ainvoke(
                    SearchCodeInput(
                        pattern=pattern,
                        directory=str(artifacts_base),
                        file_extensions=[".py", ".js", ".ts", ".yaml", ".yml", ".html", ".css"],
                    )
                )
                if search_out and not (isinstance(search_out, str) and search_out.startswith("Error")):
                    search_context = f"Repo search (pattern '{pattern}'):\n{search_out[:3000]}"
            except Exception as e:
                log.debug("Worker: repo_search failed: %s", e)

        latest = state.get_latest_critique()
        critique_block = ""
        if latest:
            critique_block = (
                f"Latest critique (verdict={latest.verdict}):\n"
                f"Reasons: {latest.reasons}\n"
                f"Suggested changes: {latest.suggested_changes}\n"
                f"Blocking issues: {latest.blocking_issues}"
            )
        else:
            critique_block = "No prior critique yet."

        system_prompt = get_worker_system_prompt()
        # Build a focused web policy snippet for this subtask's target_files
        policy_block = ""
        try:
            from ..web_policy import get_policy_for_target_files

            policy_block = get_policy_for_target_files(current.target_files or [])
        except Exception:
            policy_block = ""

        combined_search_context = search_context
        if policy_block:
            if combined_search_context:
                combined_search_context = f"{combined_search_context}\n\n{policy_block}"
            else:
                combined_search_context = policy_block

        user_prompt = get_worker_user_prompt(
            state.objective,
            state.requirement_doc or "",
            state.design_spec or "",
            current.description,
            current.notes or "",
            critique_block,
            file_context,
            combined_search_context,
        )

        # Use code_generation_tool cho single .js/.css/.html/.json khi có (chất lượng tốt hơn, ít truncate)
        single_path = ""
        ext = ""
        use_code_gen = (
            code_gen_fn is not None
            and len(paths_to_edit) == 1
            and paths_to_edit[0]
        )
        if use_code_gen:
            single_path = (paths_to_edit[0] or "").strip().replace("\\", "/")
            if "/" in single_path:
                single_path = single_path.split("/")[-1]
            ext = single_path.lower().split(".")[-1] if "." in single_path else ""
            use_code_gen = ext in ("js", "css", "html", "json")

        response = None
        if use_code_gen and code_gen_fn:
            lang_map = {"js": "JavaScript", "css": "CSS", "html": "HTML"}
            lang = lang_map.get(ext, "JavaScript")
            code_query = (
                user_prompt
                + "\n\nOutput ONLY the complete file content for "
                + single_path
                + ". No explanations, no commentary. Return the full file exactly as it should be written (no markdown fences)."
            )
            try:
                raw = await code_gen_fn.ainvoke(
                    {"query": code_query, "programming_language": lang}
                )
                content = raw if isinstance(raw, str) else getattr(raw, "content", str(raw))
                content = _strip_code_fences(content)
                response = CodeEditOutput(file_path=single_path, content=content or "")
                log.info("Worker: used code_generation_tool for %s", single_path)
            except Exception as e:
                log.warning("Worker: code_generation_tool failed, falling back to LLM: %s", e)
                response = None

        if response is None:
            try:
                response = await structured_llm.ainvoke(
                    [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
                )
            except Exception as e:
                log.warning("Worker: LLM structured output failed (retry): %s", e)
                state.subtask_retry_count = {**state.subtask_retry_count, current.id: retry_count + 1}
                state.updated_at = datetime.now().isoformat()
                return state

        # Nếu LLM không trả về file_path mà subtask chỉ target đúng 1 file,
        # ép dùng luôn target file đó (tránh mất file như products.json).
        if response and (not getattr(response, "file_path", None)) and len(paths_to_edit) == 1 and paths_to_edit[0]:
            target_name = (paths_to_edit[0] or "").strip().replace("\\", "/")
            if "/" in target_name:
                target_name = target_name.split("/")[-1]
            response.file_path = target_name

        if not response or not response.file_path or not response.content:
            log.warning("Worker: LLM returned empty file_path or content (retry)")
            state.subtask_retry_count = {**state.subtask_retry_count, current.id: retry_count + 1}
            state.updated_at = datetime.now().isoformat()
            return state

        response_path_normalized = _strip_output_prefix(response.file_path)
        edit_path = Path(response_path_normalized) if response_path_normalized else Path(response.file_path.strip())
        if not edit_path.is_absolute():
            edit_path = (artifacts_base / (response_path_normalized or response.file_path.strip())).resolve()

        # Reliability: backup before write when backup_dir set (for rollback on fatal)
        if state.backup_dir and edit_path.exists():
            try:
                existing = edit_path.read_text(encoding="utf-8")
                try:
                    rel = edit_path.relative_to(repo_path)
                except ValueError:
                    try:
                        rel = edit_path.relative_to(artifacts_base)
                    except ValueError:
                        rel = Path(edit_path.name)
                save_backup(Path(state.backup_dir), str(rel), existing)
            except Exception as e:
                log.debug("Worker: backup before write failed: %s", e)

        try:
            await file_writer_fn.ainvoke(
                WriteFileInput(
                    file_path=str(edit_path),
                    content=response.content,
                    create_directories=True,
                    encoding="utf-8",
                )
            )
        except Exception as e:
            log.warning("Worker: file_writer failed for %s (retry): %s", edit_path, e)
            state.subtask_retry_count = {**state.subtask_retry_count, current.id: retry_count + 1}
            state.updated_at = datetime.now().isoformat()
            return state

        try:
            rel_artifact = str(edit_path.relative_to(repo_path))
        except ValueError:
            rel_artifact = str(edit_path)
        artifacts[rel_artifact] = ArtifactMetadata(
            path=rel_artifact,
            created_at=now,
            modified_at=datetime.now().isoformat(),
            checksum=None,
            status="draft",
        )
        if subtask_idx is not None and subtask_idx < len(new_subtasks):
            new_subtasks[subtask_idx] = new_subtasks[subtask_idx].model_copy(
                update={"status": "done"}
            )
        state.subtasks = new_subtasks
        state.artifacts = artifacts
        state.updated_at = datetime.now().isoformat()
        return state

    yield FunctionInfo.from_fn(
        _worker,
        input_schema=TaskState,
        description=config.description,
    )
