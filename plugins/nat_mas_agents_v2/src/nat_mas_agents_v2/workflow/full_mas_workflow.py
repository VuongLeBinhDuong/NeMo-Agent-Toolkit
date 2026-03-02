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

"""Full MAS workflow: Product → Architect → (Planner → Worker → Executor → Critic) until done."""

import logging

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

from ..models import TaskState

log = logging.getLogger(__name__)


class FullMASWorkflowConfig(FunctionBaseConfig, name="full_mas_workflow"):
    """Configuration for the full MAS: Product → Architect → code loop."""

    product: FunctionRef = Field(description="Function reference for product_step (Requirement Agent)")
    architect: FunctionRef = Field(description="Function reference for architect_step (Design Agent)")
    code_loop: FunctionRef = Field(
        description="Function reference for code_loop_workflow (Planner → Worker → Executor → Critic)",
    )
    description: str = Field(
        default="Full MAS: Product (PRD) → Architect (Design) → Planner → Worker → Executor → Critic.",
        description="Description of the workflow",
    )


@register_function(config_type=FullMASWorkflowConfig)
async def full_mas_workflow(config: FullMASWorkflowConfig, builder: Builder):
    """Orchestrator: run Product → Architect → code_loop_workflow."""

    log.info("Initializing full_mas_workflow")

    product_fn = builder.get_function(config.product)
    architect_fn = builder.get_function(config.architect)
    code_loop_fn = builder.get_function(config.code_loop)

    async def _run(initial_state: TaskState) -> TaskState:
        state = initial_state.model_copy(deep=True)
        if state.status not in ("pending", "in_progress"):
            return state

        # 1) Product Agent: clarify request → requirement_doc
        log.info("Full MAS: running Product (Requirement) step")
        state = await product_fn.ainvoke(state)
        if state.status in ("success", "failed", "partial_success"):
            return state

        # 2) Architect Agent: requirement_doc → design_spec
        log.info("Full MAS: running Architect (Design) step")
        state = await architect_fn.ainvoke(state)
        if state.status in ("success", "failed", "partial_success"):
            return state

        # 3) Code loop: Planner → Worker → Executor → Critic until done
        log.info("Full MAS: running code loop (Planner → Worker → Executor → Critic)")
        state = await code_loop_fn.ainvoke(state)
        return state

    yield FunctionInfo.from_fn(
        _run,
        input_schema=TaskState,
        description=config.description,
    )
