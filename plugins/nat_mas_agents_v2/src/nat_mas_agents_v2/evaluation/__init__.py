# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Evaluation and testing harness for MAS V2.

- run_workflow_with_logging: run code loop with state logged each step
- BenchmarkTask / run_benchmark_task / run_benchmark_suite: task benchmarks and metrics
- replay_from_log_dir / load_state_at_iteration: replay failed or past runs from saved state
"""

from .benchmark import (
    BenchmarkResult,
    BenchmarkTask,
    load_benchmark_tasks_from_json,
    run_benchmark_suite,
    run_benchmark_task,
)
from .replay import (
    load_latest_state,
    load_state_at_iteration,
    list_state_snapshots,
    replay_from_log_dir,
)
from .state_logger import (
    load_state_from_path,
    run_workflow_with_logging,
    save_state_to_path,
    StepRecord,
)

__all__ = [
    "BenchmarkResult",
    "BenchmarkTask",
    "load_benchmark_tasks_from_json",
    "load_latest_state",
    "load_state_at_iteration",
    "list_state_snapshots",
    "load_state_from_path",
    "replay_from_log_dir",
    "run_benchmark_suite",
    "run_benchmark_task",
    "run_workflow_with_logging",
    "save_state_to_path",
    "StepRecord",
]
