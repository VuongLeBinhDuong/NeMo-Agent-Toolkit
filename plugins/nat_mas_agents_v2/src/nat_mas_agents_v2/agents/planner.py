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

"""Planner agent: decompose objective into incremental subtasks or refine plan from critique."""

import logging
from datetime import datetime
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import LLMRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

from ..models import Subtask, TaskState
from ..prompt_templates import get_planner_system_prompt, get_planner_user_prompt
from ..structured_output_schema import PlannerOutput, SubtaskPlanItem

log = logging.getLogger(__name__)


class PlannerStepConfig(FunctionBaseConfig, name="planner_step"):
    """Configuration for the Planner step."""

    llm_name: LLMRef = Field(
        description="Reasoning LLM for task decomposition and refinement from critique.",
    )
    description: str = Field(
        default="Decompose objective into incremental subtasks or refine plan from critique using reasoning LLM.",
        description="Description of the planner step",
    )


@register_function(config_type=PlannerStepConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def planner_step(config: PlannerStepConfig, builder: Builder):
    """Planner step: call reasoning LLM to decompose or refine subtasks from objective and critique."""

    log.info("Initializing planner_step")

    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)
    structured_llm = llm.with_structured_output(PlannerOutput)

    def _extract_file_structure(design_spec: str | None) -> List[str]:
        """Parse design_spec text to recover the File Structure list."""
        if not design_spec:
            return []
        lines = design_spec.splitlines()
        files: List[str] = []
        in_fs = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## ") and "File Structure" in stripped:
                in_fs = True
                continue
            if in_fs:
                # Stop when the next section starts
                if stripped.startswith("## "):
                    break
                if stripped.startswith("- "):
                    name = stripped[2:].strip()
                    if name:
                        files.append(name)
        return files

    async def _planner(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        state.iteration += 1
        state.status = "in_progress"

        # 1) Nếu đã có subtasks rồi, Planner không replan nữa mà chỉ chọn subtask tiếp theo.
        if state.subtasks:
            current_idx = 0
            for i, st in enumerate(state.subtasks):
                if st.status != "done":
                    current_idx = i
                    break
            state.current_subtask_index = current_idx if state.subtasks else None
            state.updated_at = datetime.now().isoformat()
            log.info("Planner (one-shot): reuse existing %s subtasks, current_index=%s", len(state.subtasks), state.current_subtask_index)
            return state

        # 2) Chưa có subtasks: tạo một lần danh sách subtasks dựa trên File Structure trong design_spec.
        file_structure = _extract_file_structure(state.design_spec)
        new_subtasks: List[Subtask] = []
        if file_structure:
            for fname in file_structure:
                key = (fname or "").strip().replace("\\", "/")
                if not key:
                    continue
                if "/" in key:
                    key = key.split("/")[-1]
                subtask_id = f"FS-{key}"
                new_subtasks.append(
                    Subtask(
                        id=subtask_id,
                        description=f"Implement {key} exactly according to the Design Spec File Structure and Per-file Requirements.",
                        status="pending",
                        target_files=[key],
                        notes="One-shot plan: auto-created from design_spec File Structure.",
                    )
                )
        else:
            # Fallback: nếu không có File Structure thì tạo một subtask tổng quát cho objective.
            new_subtasks.append(
                Subtask(
                    id="TS-001",
                    description=state.objective,
                    status="pending",
                    target_files=[],
                    notes="One-shot plan fallback: no File Structure in design_spec.",
                )
            )

        state.subtasks = new_subtasks
        state.current_subtask_index = 0 if new_subtasks else None
        state.updated_at = datetime.now().isoformat()
        log.info("Planner (one-shot): created %s subtasks from design_spec, current_index=%s", len(new_subtasks), state.current_subtask_index)
        return state

    yield FunctionInfo.from_fn(
        _planner,
        input_schema=TaskState,
        description=config.description,
    )
