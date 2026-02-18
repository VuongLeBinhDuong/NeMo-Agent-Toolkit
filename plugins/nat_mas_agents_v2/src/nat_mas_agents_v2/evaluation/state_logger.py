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

"""Log TaskState after each workflow step for debugging, audit, and replay."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from nat.builder.builder import Builder
from nat.data_models.component_ref import FunctionRef

from ..models import TaskState

log = logging.getLogger(__name__)


@dataclass
class StepRecord:
    """Single step in a run: step name, 0-based index, and state after the step."""

    step: str  # "planner" | "worker" | "executor" | "critic"
    iteration: int  # 0-based loop iteration
    state: TaskState
    state_json: Optional[dict] = None  # populated when persisting to disk


def _state_to_json_dict(state: TaskState) -> dict:
    """Serialize TaskState to JSON-serializable dict."""
    return state.model_dump(mode="json")


def save_state_to_path(state: TaskState, path: Path) -> None:
    """Write TaskState to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(_state_to_json_dict(state), f, indent=2, ensure_ascii=False)


def load_state_from_path(path: Path) -> TaskState:
    """Load TaskState from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return TaskState.from_dict(data)


async def run_workflow_with_logging(
    builder: Builder,
    *,
    planner: FunctionRef,
    worker: FunctionRef,
    executor: FunctionRef,
    critic: FunctionRef,
    initial_state: TaskState,
    max_iterations: int = 15,
    log_dir: Optional[Path] = None,
    on_step: Optional[Callable[[str, int, TaskState], None]] = None,
) -> tuple[TaskState, List[StepRecord]]:
    """Run the code loop (Planner → Worker → Executor → Critic) with state logging each step.

    Same orchestration as code_loop_workflow, but after each step we append a StepRecord
    and optionally write state to log_dir and/or call on_step.

    Args:
        builder: NAT Builder (with workflow config loaded).
        planner, worker, executor, critic: Function refs for the four steps.
        initial_state: Starting TaskState.
        max_iterations: Max loop iterations.
        log_dir: If set, write state to log_dir/iter_{i}_{step}.json each step.
        on_step: Optional callback(step_name, iteration, state) after each step.

    Returns:
        (final_state, list of StepRecord for each step executed).
    """
    planner_fn = builder.get_function(planner)
    worker_fn = builder.get_function(worker)
    executor_fn = builder.get_function(executor)
    critic_fn = builder.get_function(critic)

    state = initial_state.model_copy(deep=True)
    if state.status not in ("pending", "in_progress"):
        return state, []

    state.status = "in_progress"
    records: List[StepRecord] = []
    step_order = ["planner", "worker", "executor", "critic"]

    for it in range(max_iterations):
        log.info("Code loop iteration %s (with logging)", it + 1)

        for step_name, step_fn in [
            ("planner", planner_fn),
            ("worker", worker_fn),
            ("executor", executor_fn),
            ("critic", critic_fn),
        ]:
            state = await step_fn.ainvoke(state)
            rec = StepRecord(step=step_name, iteration=it, state=state.model_copy(deep=True))
            if log_dir:
                rec.state_json = _state_to_json_dict(state)
                out_path = log_dir / f"iter_{it:03d}_{step_name}.json"
                save_state_to_path(state, out_path)
            records.append(rec)
            if on_step:
                on_step(step_name, it, state)

            if state.status in ("success", "failed"):
                return state, records
        if not state.should_continue():
            return state, records

    if state.status == "in_progress":
        state = state.model_copy(update={"status": "failed"})
    return state, records
