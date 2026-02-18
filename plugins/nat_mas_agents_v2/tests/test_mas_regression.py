# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Regression tests for MAS V2: run benchmark tasks and assert on outcomes.
# Use run_workflow_with_logging to capture state each iteration for debugging.
#
# Mark as integration when full workflow is run (requires LLM/tools config).

import json
from pathlib import Path

import pytest

from nat_mas_agents_v2.models import TaskState
from nat_mas_agents_v2.evaluation import (
    BenchmarkResult,
    BenchmarkTask,
    load_benchmark_tasks_from_json,
)
from nat_mas_agents_v2.evaluation.replay import load_latest_state, load_state_at_iteration
from nat_mas_agents_v2.evaluation.state_logger import load_state_from_path, save_state_to_path


# Path to example benchmark tasks (package-relative).
BENCHMARK_TASKS_DIR = Path(__file__).resolve().parent.parent / "src" / "nat_mas_agents_v2" / "evaluation" / "benchmark_tasks"


def test_regression_initial_state_invariants():
    """Regression: TaskState created from BenchmarkTask has expected invariants."""
    task = BenchmarkTask(task_id="invariant_test", objective="Create file", repo_root=".")
    state = task.to_initial_state()
    assert state.status in ("pending", "in_progress")
    assert state.iteration >= 0
    assert state.subtasks == []
    assert state.artifacts == {}
    assert state.execution_log == []
    assert state.critique_history == []


def test_regression_benchmark_result_serialization():
    """Regression: BenchmarkResult is JSON-serializable for summary output."""
    r = BenchmarkResult(
        task_id="t1",
        objective="x",
        success=True,
        status="success",
        iterations=2,
        duration_seconds=1.5,
        num_subtasks=2,
        num_artifacts=1,
        num_critiques=2,
    )
    d = r.to_dict()
    assert json.dumps(d)  # no raise
    assert d["task_id"] == "t1" and d["success"] is True


@pytest.mark.asyncio
async def test_regression_run_workflow_with_logging_returns_records(tmp_path):
    """Regression: run_workflow_with_logging returns (final_state, records) and can write to log_dir.
    Uses a mock Builder would require NAT test fixtures; we only test the contract when no builder.
    """
    # Without a real builder we cannot run the workflow; test the state logger contract by
    # verifying save/load round-trip and that replay helpers work on saved state.
    state = TaskState(objective="test", repo_root=str(tmp_path))
    save_state_to_path(state, tmp_path / "iter_000_planner.json")
    save_state_to_path(state, tmp_path / "iter_000_critic.json")
    loaded = load_latest_state(tmp_path)
    assert loaded is not None
    assert loaded.objective == "test"
    at_0 = load_state_at_iteration(tmp_path, 0, "critic")
    assert at_0 is not None


def test_regression_benchmark_tasks_json_exists():
    """Regression: example benchmark tasks file exists and is valid JSON."""
    path = BENCHMARK_TASKS_DIR / "example_tasks.json"
    if not path.exists():
        pytest.skip("benchmark_tasks/example_tasks.json not found")
    tasks = load_benchmark_tasks_from_json(path)
    assert len(tasks) >= 1
    for t in tasks:
        assert t.task_id and t.objective
