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

"""Product Agent (Requirement Agent): clarify user request, write short PRD, define acceptance criteria."""

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
from ..prompt_templates import get_product_system_prompt, get_product_user_prompt
from ..structured_output_schema import RequirementDocOutput
from ..tools import WriteFileInput

log = logging.getLogger(__name__)


class ProductStepConfig(FunctionBaseConfig, name="product_step"):
    """Configuration for the Product (Requirement) step."""

    llm_name: LLMRef = Field(
        description="LLM for requirement clarification and PRD writing.",
    )
    description: str = Field(
        default="Clarify user request, write short PRD, define acceptance criteria.",
        description="Description of the product step",
    )


def _get_write_file_fn(builder: Builder):
    """Resolve write_file or file_writer tool."""
    for name in ("write_file", "file_writer"):
        try:
            return builder.get_function(name)
        except Exception:
            continue
    return None


async def _write_requirement_txt(state: TaskState, write_file_fn) -> None:
    """Write state.requirement_doc to requirement_doc.txt (under output_dir if set)."""
    if not state.requirement_doc or not write_file_fn:
        return
    try:
        repo_path = Path(state.repo_root or ".").resolve()
        if state.output_dir and str(state.output_dir).strip():
            out_dir = (repo_path / str(state.output_dir).strip()).resolve()
            out_dir.mkdir(parents=True, exist_ok=True)
        else:
            out_dir = repo_path
        txt_path = out_dir / "requirement_doc.txt"
        await write_file_fn.ainvoke(
            WriteFileInput(
                file_path=str(txt_path),
                content=state.requirement_doc,
                create_directories=True,
                encoding="utf-8",
            )
        )
        log.info("Product: wrote requirement_doc.txt to %s", txt_path)
    except Exception as e:
        log.warning("Product: failed to write requirement_doc.txt: %s", e)


@register_function(config_type=ProductStepConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def product_step(config: ProductStepConfig, builder: Builder):
    """Product step: turn user objective into structured requirement doc (PRD + acceptance criteria)."""

    log.info("Initializing product_step")

    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    structured_llm = llm.with_structured_output(RequirementDocOutput)
    write_file_fn = _get_write_file_fn(builder)

    async def _product(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        if state.requirement_doc:
            log.info("Product: requirement_doc already set, skipping")
            return state

        system_prompt = get_product_system_prompt()
        user_prompt = get_product_user_prompt(state.objective)

        try:
            response: RequirementDocOutput = await structured_llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        except Exception as e:
            log.warning("Product: LLM failed, using objective as requirement_doc: %s", e)
            state.requirement_doc = f"# Requirements (fallback)\n\nSummary: {state.objective}\n\nAcceptance criteria: (see objective above)"
            state.updated_at = datetime.now().isoformat()
            await _write_requirement_txt(state, write_file_fn)
            return state

        if not response:
            state.requirement_doc = f"# Requirements\n\nSummary: {state.objective}"
            state.updated_at = datetime.now().isoformat()
            await _write_requirement_txt(state, write_file_fn)
            return state

        lines = [
            "# Product Requirements (PRD)",
            "",
            "## Summary",
            response.summary.strip(),
            "",
            "## Acceptance Criteria",
        ]
        for i, ac in enumerate(response.acceptance_criteria or [], 1):
            lines.append(f"{i}. {ac.strip()}")
        if response.scope and response.scope.strip():
            lines.extend(["", "## Scope / Constraints", response.scope.strip()])

        state.requirement_doc = "\n".join(lines)
        state.updated_at = datetime.now().isoformat()
        log.info("Product: wrote requirement_doc (%s chars, %s criteria)", len(state.requirement_doc), len(response.acceptance_criteria or []))
        await _write_requirement_txt(state, write_file_fn)
        return state

    yield FunctionInfo.from_fn(
        _product,
        input_schema=TaskState,
        description=config.description,
    )
