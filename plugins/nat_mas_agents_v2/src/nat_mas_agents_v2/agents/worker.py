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
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import BaseModel, Field

from ..models import ArtifactMetadata, TaskState
from ..reliability.rollback import save_backup
from ..tools import (
    ListFilesInput,
    ReadFileInput,
    SearchCodeInput,
    WriteFileInput,
)

log = logging.getLogger(__name__)


class _CodeEditOutput(BaseModel):
    """Structured LLM output: one file path and full content (patch applied as full file)."""

    file_path: str = Field(description="Relative path from repo_root or absolute path")
    content: str = Field(description="Complete file content to write")


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


@register_function(config_type=WorkerStepConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def worker_step(config: WorkerStepConfig, builder: Builder):
    """Worker step: tool-grounded read-modify-write using file_reader, file_writer, repo_search."""

    log.info("Initializing worker_step (file_reader / file_writer / repo_search)")

    file_reader_fn = _get_tool(builder, "file_reader", "read_file")
    file_writer_fn = _get_tool(builder, "file_writer", "write_file")
    repo_search_fn = _get_tool(builder, "repo_search", "search_code")
    try:
        list_files_fn = builder.get_function("list_files")
    except Exception:
        list_files_fn = None

    if not file_reader_fn or not file_writer_fn:
        raise RuntimeError(
            "Worker requires at least one of (file_reader, read_file) and one of (file_writer, write_file)."
        )

    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    structured_llm = llm.with_structured_output(_CodeEditOutput)

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
        artifacts = dict(state.artifacts)
        now = datetime.now().isoformat()

        file_context_parts = []
        paths_to_edit = list(current.target_files) if current.target_files else []

        if not paths_to_edit and list_files_fn:
            try:
                listing = await list_files_fn.ainvoke(
                    ListFilesInput(directory=repo_root, recursive=False)
                )
                file_context_parts.append(f"Repository listing:\n{listing or ''}")
            except Exception as e:
                log.debug("Worker: list_files failed: %s", e)

        for rel_path in paths_to_edit:
            if not rel_path or not rel_path.strip():
                continue
            abs_path = (repo_path / rel_path.strip()).resolve()
            try:
                out = await file_reader_fn.ainvoke(
                    ReadFileInput(file_path=str(abs_path), encoding="utf-8")
                )
                file_context_parts.append(f"--- File: {rel_path} ---\n{out}")
            except Exception as e:
                file_context_parts.append(f"--- File: {rel_path} (read error: {e}) ---\n(create or fix this file)")

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
                        directory=repo_root,
                        file_extensions=[".py", ".js", ".ts", ".yaml", ".yml"],
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

        system_prompt = (
            "You are a code-generation agent. You receive: task objective, current subtask, file content (from file_reader), "
            "optional repo search context, and optional critique. Respond with exactly one file edit: the file_path "
            "(relative to repo_root or absolute) and the complete new content for that file. "
            "For new files, set file_path to the path to create and content to the full file content. "
            "Do not include explanations; only output the structured file_path and content."
        )
        user_prompt = (
            f"Objective: {state.objective}\n\n"
            f"Current subtask: {current.description}\n"
            f"Notes: {current.notes or 'None'}\n\n"
            f"{critique_block}\n\n"
            f"File context (from file_reader):\n{file_context}"
        )
        if search_context:
            user_prompt += f"\n\n{search_context}"

        try:
            response: _CodeEditOutput = await structured_llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        except Exception as e:
            log.warning("Worker: LLM structured output failed (retry): %s", e)
            state.subtask_retry_count = {**state.subtask_retry_count, current.id: retry_count + 1}
            state.updated_at = datetime.now().isoformat()
            return state

        if not response or not response.file_path or not response.content:
            log.warning("Worker: LLM returned empty file_path or content (retry)")
            state.subtask_retry_count = {**state.subtask_retry_count, current.id: retry_count + 1}
            state.updated_at = datetime.now().isoformat()
            return state

        edit_path = Path(response.file_path.strip())
        if not edit_path.is_absolute():
            edit_path = (repo_path / response.file_path.strip()).resolve()

        # Reliability: backup before write when backup_dir set (for rollback on fatal)
        if state.backup_dir and edit_path.exists():
            try:
                existing = edit_path.read_text(encoding="utf-8")
                try:
                    rel = edit_path.relative_to(repo_path)
                except ValueError:
                    rel = edit_path.name
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
