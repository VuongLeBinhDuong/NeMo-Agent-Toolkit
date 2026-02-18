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

"""Task benchmark: run MAS on defined tasks and collect metrics for regression and stability."""

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from nat.builder.builder import Builder
from nat.data_models.component_ref import FunctionRef

from ..models import TaskState
from .state_logger import run_workflow_with_logging, save_state_to_path

log = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a single benchmark task run."""

    task_id: str
    objective: str
    success: bool
    status: str  # "success" | "failed" | "in_progress"
    iterations: int
    duration_seconds: float
    num_subtasks: int
    num_artifacts: int
    num_critiques: int
    log_dir: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkTask:
    """Definition of a benchmark task (initial state + optional expectations)."""

    task_id: str
    objective: str
    repo_root: str = "."
    expect_success: bool = True  # for regression: assert success == expect_success

    def to_initial_state(self) -> TaskState:
        return TaskState(
            objective=self.objective,
            repo_root=self.repo_root,
            status="pending",
        )


async def run_benchmark_task(
    builder: Builder,
    task: BenchmarkTask,
    *,
    planner: FunctionRef,
    worker: FunctionRef,
    executor: FunctionRef,
    critic: FunctionRef,
    max_iterations: int = 15,
    log_dir: Optional[Path] = None,
) -> BenchmarkResult:
    """Run a single benchmark task and return metrics."""
    initial = task.to_initial_state()
    start = time.perf_counter()
    try:
        final_state, records = await run_workflow_with_logging(
            builder,
            planner=planner,
            worker=worker,
            executor=executor,
            critic=critic,
            initial_state=initial,
            max_iterations=max_iterations,
            log_dir=log_dir,
        )
    except Exception as e:
        duration = time.perf_counter() - start
        return BenchmarkResult(
            task_id=task.task_id,
            objective=task.objective,
            success=False,
            status="failed",
            iterations=0,
            duration_seconds=duration,
            num_subtasks=0,
            num_artifacts=0,
            num_critiques=0,
            error=str(e),
        )

    duration = time.perf_counter() - start
    steps_per_iter = 4
    iterations = (len(records) + steps_per_iter - 1) // steps_per_iter if records else 0

    return BenchmarkResult(
        task_id=task.task_id,
        objective=task.objective,
        success=final_state.status == "success",
        status=final_state.status,
        iterations=iterations,
        duration_seconds=round(duration, 2),
        num_subtasks=len(final_state.subtasks),
        num_artifacts=len(final_state.artifacts),
        num_critiques=len(final_state.critique_history),
        log_dir=str(log_dir) if log_dir else None,
    )


async def run_benchmark_suite(
    builder: Builder,
    tasks: List[BenchmarkTask],
    *,
    planner: FunctionRef,
    worker: FunctionRef,
    executor: FunctionRef,
    critic: FunctionRef,
    max_iterations: int = 15,
    output_dir: Optional[Path] = None,
) -> List[BenchmarkResult]:
    """Run multiple benchmark tasks and optionally write results to output_dir."""
    results: List[BenchmarkResult] = []
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    for task in tasks:
        log_dir = (output_dir / task.task_id) if output_dir else None
        res = await run_benchmark_task(
            builder,
            task,
            planner=planner,
            worker=worker,
            executor=executor,
            critic=critic,
            max_iterations=max_iterations,
            log_dir=log_dir,
        )
        results.append(res)

    if output_dir:
        summary_path = output_dir / "benchmark_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        log.info("Wrote benchmark summary to %s", summary_path)

    return results


def load_benchmark_tasks_from_json(path: Path) -> List[BenchmarkTask]:
    """Load benchmark tasks from a JSON file. Format: list of {task_id, objective, repo_root?, expect_success?}."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        BenchmarkTask(
            task_id=item["task_id"],
            objective=item["objective"],
            repo_root=item.get("repo_root", "."),
            expect_success=item.get("expect_success", True),
        )
        for item in data
    ]
