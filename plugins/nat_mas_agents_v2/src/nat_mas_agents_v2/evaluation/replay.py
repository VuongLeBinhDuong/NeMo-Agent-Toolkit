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

"""Replay failed or past runs from saved state snapshots."""

import logging
from pathlib import Path
from typing import Optional

from nat.builder.builder import Builder
from nat.data_models.component_ref import FunctionRef

from ..models import TaskState
from .state_logger import load_state_from_path, run_workflow_with_logging

log = logging.getLogger(__name__)


def list_state_snapshots(log_dir: Path) -> list[tuple[int, str, Path]]:
    """List state snapshot files in log_dir. Returns [(iteration, step_name, path), ...] sorted by iter then step."""
    if not log_dir.is_dir():
        return []
    out = []
    for p in log_dir.iterdir():
        if not p.suffix == ".json" or p.name == "benchmark_summary.json":
            continue
        # iter_001_planner.json
        name = p.stem
        if name.startswith("iter_") and "_" in name[5:]:
            try:
                iter_str, step = name[5:].split("_", 1)
                out.append((int(iter_str), step, p))
            except ValueError:
                continue
    out.sort(key=lambda x: (x[0], ["planner", "worker", "executor", "critic"].index(x[1]) if x[1] in ("planner", "worker", "executor", "critic") else 99))
    return out


def load_latest_state(log_dir: Path) -> Optional[TaskState]:
    """Load the latest state snapshot from log_dir (by iteration and step order)."""
    snapshots = list_state_snapshots(log_dir)
    if not snapshots:
        return None
    _, _, path = snapshots[-1]
    return load_state_from_path(path)


def load_state_at_iteration(log_dir: Path, iteration: int, after_step: str = "critic") -> Optional[TaskState]:
    """Load state at the end of a given iteration (after critic step)."""
    snapshots = list_state_snapshots(log_dir)
    step_order = ["planner", "worker", "executor", "critic"]
    for it, step, path in snapshots:
        if it == iteration and step == after_step:
            return load_state_from_path(path)
    return None


async def replay_from_log_dir(
    builder: Builder,
    log_dir: Path,
    *,
    planner: FunctionRef,
    worker: FunctionRef,
    executor: FunctionRef,
    critic: FunctionRef,
    from_iteration: Optional[int] = None,
    max_iterations: int = 15,
    output_log_dir: Optional[Path] = None,
) -> TaskState:
    """Replay a run from saved state. If from_iteration is None, uses latest snapshot; else uses state at end of that iteration."""
    if from_iteration is not None:
        state = load_state_at_iteration(log_dir, from_iteration)
    else:
        state = load_latest_state(log_dir)
    if state is None:
        raise FileNotFoundError(f"No state snapshot found in {log_dir}")

    # Reset status so the loop can run again
    state = state.model_copy(update={"status": "in_progress"})
    final_state, _ = await run_workflow_with_logging(
        builder,
        planner=planner,
        worker=worker,
        executor=executor,
        critic=critic,
        initial_state=state,
        max_iterations=max_iterations,
        log_dir=output_log_dir,
    )
    return final_state
