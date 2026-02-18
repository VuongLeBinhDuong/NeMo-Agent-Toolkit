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
from pydantic import BaseModel, Field

from ..models import Subtask, TaskState

log = logging.getLogger(__name__)


class _SubtaskPlanItem(BaseModel):
    """One subtask as produced by the reasoning LLM."""

    id: str = Field(description="Short unique id, e.g. '1', '2', 'fix-tests'")
    description: str = Field(description="Clear description of what to do")
    target_files: List[str] = Field(
        default_factory=list,
        description="File paths this subtask will touch (relative to repo_root)",
    )
    notes: str = Field(
        default="",
        description="Optional context or constraints",
    )


class _PlannerOutput(BaseModel):
    """Structured output from the planner LLM: incremental subtasks."""

    subtasks: List[_SubtaskPlanItem] = Field(
        description="Ordered list of subtasks (incremental decomposition or refinement)",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for this plan (for logging)",
    )


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
    structured_llm = llm.with_structured_output(_PlannerOutput)

    async def _planner(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        state.iteration += 1
        state.status = "in_progress"

        existing_block = ""
        if state.subtasks:
            existing_block = "Current subtasks (preserve order; refine or add based on critique):\n"
            for i, st in enumerate(state.subtasks):
                existing_block += (
                    f"  {i + 1}. [id={st.id} status={st.status}] {st.description}\n"
                    f"      target_files={st.target_files} notes={st.notes or ''}\n"
                )
        else:
            existing_block = "No subtasks yet. Produce initial incremental decomposition."

        latest = state.get_latest_critique()
        critique_block = "No critique yet."
        if latest:
            critique_block = (
                f"Latest critique (verdict={latest.verdict}):\n"
                f"Reasons: {latest.reasons}\n"
                f"Suggested changes: {latest.suggested_changes}\n"
                f"Blocking issues: {latest.blocking_issues}"
            )

        exec_block = ""
        if state.last_tests:
            t = state.last_tests
            exec_block = f"Last test result: passed={t.passed} failed={t.failed} errors={t.errors}. Details: {t.details[:500]}"
        if state.execution_log:
            last_log = state.execution_log[-1]
            exec_block += f"\nLast execution: {last_log.step} exit_code={last_log.exit_code}"

        system_prompt = (
            "You are a planning agent for a coding workflow. Given an objective and optional current subtasks and critique, "
            "output an ordered list of incremental subtasks. Each subtask has: id (short, unique), description (one clear task), "
            "target_files (list of file paths to create or modify), notes (optional). "
            "If there are no subtasks yet: decompose the objective into a few concrete, incremental steps. "
            "If there are existing subtasks and a critique: refine the plan (e.g. add a step to fix failing tests, or adjust descriptions). "
            "Preserve completed work: keep done subtasks in the same order; only add or refine pending/upcoming ones. "
            "Output only the structured list and brief reasoning."
        )
        user_prompt = (
            f"Objective: {state.objective}\n\n"
            f"{existing_block}\n\n"
            f"Critique:\n{critique_block}\n\n"
            f"Execution context:\n{exec_block or 'None'}"
        )

        try:
            response: _PlannerOutput = await structured_llm.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
        except Exception as e:
            log.warning("Planner: LLM failed, falling back to rule-based: %s", e)
            if not state.subtasks:
                state.subtasks = [
                    Subtask(
                        id="1",
                        description=state.objective,
                        status="pending",
                        target_files=[],
                        notes="Initial task (LLM fallback)",
                    )
                ]
                state.current_subtask_index = 0
            state.updated_at = datetime.now().isoformat()
            return state

        if not response or not response.subtasks:
            log.warning("Planner: LLM returned no subtasks, keeping existing plan")
            if not state.subtasks:
                state.subtasks = [
                    Subtask(
                        id="1",
                        description=state.objective,
                        status="pending",
                        target_files=[],
                        notes="Fallback single task",
                    )
                ]
                state.current_subtask_index = 0
            state.updated_at = datetime.now().isoformat()
            return state

        if response.reasoning:
            log.info("Planner reasoning: %s", response.reasoning[:200])

        new_subtasks: List[Subtask] = []
        for i, item in enumerate(response.subtasks):
            if i < len(state.subtasks) and state.subtasks[i].status == "done":
                existing = state.subtasks[i]
                new_subtasks.append(
                    existing.model_copy(
                        update={
                            "description": item.description,
                            "target_files": item.target_files,
                            "notes": item.notes or existing.notes,
                        }
                    )
                )
            else:
                new_subtasks.append(
                    Subtask(
                        id=item.id or str(i + 1),
                        description=item.description,
                        status="pending",
                        target_files=item.target_files or [],
                        notes=item.notes or None,
                    )
                )

        current_idx = 0
        for i, st in enumerate(new_subtasks):
            if st.status != "done":
                current_idx = i
                break

        state.subtasks = new_subtasks
        state.current_subtask_index = current_idx if new_subtasks else None
        state.updated_at = datetime.now().isoformat()
        log.info("Planner: %s subtasks, current_index=%s", len(new_subtasks), state.current_subtask_index)
        return state

    yield FunctionInfo.from_fn(
        _planner,
        input_schema=TaskState,
        description=config.description,
    )
