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

"""Architect Agent (Design Agent): design modules, file structure, and API from requirement doc."""

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
from pydantic import Field

from ..models import TaskState
from ..prompt_templates import get_architect_system_prompt, get_architect_user_prompt
from ..structured_output_schema import DesignSpecOutput
from ..tools import WriteFileInput
from ..web_policy import get_dom_contract_for_design_spec

log = logging.getLogger(__name__)


class ArchitectStepConfig(FunctionBaseConfig, name="architect_step"):
    """Configuration for the Architect (Design) step."""

    llm_name: LLMRef = Field(
        description="LLM for design and architecture from requirements.",
    )
    description: str = Field(
        default="Design modules, file structure, and API from requirement doc.",
        description="Description of the architect step",
    )


@register_function(config_type=ArchitectStepConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def architect_step(config: ArchitectStepConfig, builder: Builder):
    """Architect step: turn requirement doc into design spec (file structure, modules, API)."""

    log.info("Initializing architect_step")

    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    structured_llm = llm.with_structured_output(DesignSpecOutput)

    # Reuse same pattern as Product agent: write a human-readable txt beside artifacts
    def _get_write_file_fn():
        for name in ("write_file", "file_writer"):
            try:
                return builder.get_function(name)
            except Exception:
                continue
        return None

    write_file_fn = _get_write_file_fn()

    async def _write_design_txt(state: TaskState) -> None:
        """Write state.design_spec to design_spec.txt (under output_dir if set)."""
        if not state.design_spec or not write_file_fn:
            return
        try:
            repo_path = Path(state.repo_root or ".").resolve()
            if state.output_dir and str(state.output_dir).strip():
                out_dir = (repo_path / str(state.output_dir).strip()).resolve()
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = repo_path
            txt_path = out_dir / "design_spec.txt"
            await write_file_fn.ainvoke(
                WriteFileInput(
                    file_path=str(txt_path),
                    content=state.design_spec,
                    create_directories=True,
                    encoding="utf-8",
                )
            )
            log.info("Architect: wrote design_spec.txt to %s", txt_path)
        except Exception as e:
            log.warning("Architect: failed to write design_spec.txt: %s", e)

    async def _architect(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        if state.design_spec:
            log.info("Architect: design_spec already set, skipping")
            return state

        requirement_input = state.requirement_doc or state.objective
        if not requirement_input:
            log.warning("Architect: no requirement_doc or objective, skipping")
            return state

        system_prompt = get_architect_system_prompt()
        user_prompt = get_architect_user_prompt(requirement_input, output_dir=state.output_dir)

        try:
            response: DesignSpecOutput = await structured_llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        except Exception as e:
            log.warning("Architect: LLM failed, using minimal design_spec: %s", e)
            state.design_spec = (
                "# Design Spec (fallback)\n\n"
                "File structure: (derive from requirement)\n"
                "Modules: (see requirement)\n"
            )
            state.updated_at = datetime.now().isoformat()
            await _write_design_txt(state)
            return state

        if not response:
            state.design_spec = "# Design Spec\n\n(see requirement doc)"
            state.updated_at = datetime.now().isoformat()
            await _write_design_txt(state)
            return state

        def _is_placeholder(text: str) -> bool:
            t = (text or "").strip()
            if not t:
                return True
            if "<!--" in t or "-->" in t:
                return True
            if "for EACH file in file_structure" in t or "one line 'filename:" in t:
                return True
            if t.startswith("><!--") or t.startswith("<!--"):
                return True
            return False

        def _valid_file_path(path: str) -> bool:
            p = (path or "").strip()
            if not p or "<!--" in p or ">" in p or "<" in p:
                return False
            # Allow index.html, output/styles.css, etc.
            if "/" in p or "\\" in p:
                p = p.split("/")[-1].split("\\")[-1]
            return "." in p and len(p) < 120

        # Normalize and augment file_structure to ensure critical assets exist
        raw_paths = list(response.file_structure or [])
        normalized: list[str] = []
        seen: set[str] = set()
        has_html = False
        has_css = False
        has_js = False
        for path in raw_paths:
            if not _valid_file_path(path):
                continue
            p = path.strip().replace("\\", "/")
            if "/" in p:
                p = p.split("/")[-1]
            lower = p.lower()
            if lower in seen:
                continue
            seen.add(lower)
            normalized.append(p)
            if lower.endswith(".html"):
                has_html = True
            elif lower.endswith(".css"):
                has_css = True
            elif lower.endswith(".js"):
                has_js = True

        # For web projects with HTML pages, ensure CSS, JS, and products.json when applicable
        if has_html:
            if not has_css:
                normalized.append("styles.css")
            if not has_js:
                normalized.append("app.js")
            # Add products.json if not present (product/shop sites: JS loads data from here)
            if "products.json" not in [p.lower() for p in normalized]:
                normalized.append("products.json")

        lines = [
            "# Design Spec",
            "",
            "## File Structure",
        ]
        for p in normalized:
            lines.append(f"- {p}")
        # Inject DOM/class/id and products.json contract so Worker uses same names everywhere
        lines.extend(["", "## DOM / Class & ID Contract (use exactly these in HTML, CSS, JS)", get_dom_contract_for_design_spec()])
        if response.file_requirements and not _is_placeholder(response.file_requirements):
            lines.extend(["", "## Per-file Requirements (implement exactly these)", response.file_requirements.strip()])
        if response.modules and not _is_placeholder(response.modules):
            lines.extend(["", "## Modules / Components", response.modules.strip()])
        if response.api_or_contracts and not _is_placeholder(response.api_or_contracts):
            lines.extend(["", "## API / Contracts", response.api_or_contracts.strip()])
        if response.implementation_notes and not _is_placeholder(response.implementation_notes):
            lines.extend(["", "## Implementation Notes", response.implementation_notes.strip()])

        state.design_spec = "\n".join(lines)
        state.updated_at = datetime.now().isoformat()
        await _write_design_txt(state)
        log.info(
            "Architect: wrote design_spec (%s chars, %s files)",
            len(state.design_spec),
            len(response.file_structure or []),
        )
        return state

    yield FunctionInfo.from_fn(
        _architect,
        input_schema=TaskState,
        description=config.description,
    )
