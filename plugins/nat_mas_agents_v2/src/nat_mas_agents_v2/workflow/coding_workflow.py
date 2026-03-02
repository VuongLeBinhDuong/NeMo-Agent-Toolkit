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

"""Code loop workflow: orchestration only. Planner → Worker → Executor → Critic until success or failed."""

import logging

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

from ..models import TaskState

log = logging.getLogger(__name__)

DEFAULT_MAX_ITERATIONS = 15


class CodeLoopWorkflowConfig(FunctionBaseConfig, name="code_loop_workflow"):
    """Configuration for the code loop workflow orchestrator."""

    planner: FunctionRef = Field(description="Function reference for planner_step")
    worker: FunctionRef = Field(description="Function reference for worker_step")
    executor: FunctionRef = Field(description="Function reference for executor_step")
    critic: FunctionRef = Field(description="Function reference for critic_step")
    max_iterations: int = Field(
        default=DEFAULT_MAX_ITERATIONS,
        ge=1,
        le=100,
        description="Maximum iterations before stopping",
    )
    stuck_window: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Consider stuck if last N critiques all verdict=continue",
    )
    description: str = Field(
        default="Iterative coding loop: Planner → Worker → Executor → Critic until success or failed.",
        description="Description of the workflow",
    )


@register_function(config_type=CodeLoopWorkflowConfig)
async def code_loop_workflow(config: CodeLoopWorkflowConfig, builder: Builder):
    """Orchestrator: run Planner → Worker → Executor → Critic until status is success or failed."""

    log.info("Initializing code_loop_workflow")

    planner_fn = builder.get_function(config.planner)
    worker_fn = builder.get_function(config.worker)
    executor_fn = builder.get_function(config.executor)
    critic_fn = builder.get_function(config.critic)

    async def _run(initial_state: TaskState) -> TaskState:
        state = initial_state.model_copy(deep=True)
        if state.status not in ("pending", "in_progress"):
            return state

        state.status = "in_progress"
        for _ in range(config.max_iterations):
            log.info("Code loop iteration %s", state.iteration + 1)
            state = await planner_fn.ainvoke(state)
            if state.status in ("success", "failed", "partial_success"):
                return state
            state = await worker_fn.ainvoke(state)
            if state.status in ("success", "failed", "partial_success"):
                return state
            state = await executor_fn.ainvoke(state)
            if state.status in ("success", "failed", "partial_success"):
                return state
            state = await critic_fn.ainvoke(state)

            if state.status in ("success", "failed", "partial_success"):
                return state
            if not state.should_continue():
                return state

        if state.status == "in_progress":
            state = state.model_copy(update={"status": "failed"})
        # Reliability: partial success when we have some progress but ended failed
        if state.status == "failed" and state.has_partial_progress():
            state = state.model_copy(update={"status": "partial_success"})
        return state

    yield FunctionInfo.from_fn(
        _run,
        input_schema=TaskState,
        description=config.description,
    )
