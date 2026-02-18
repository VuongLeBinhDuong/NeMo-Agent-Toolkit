# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Unit tests for evaluation harness: state save/load, benchmark task, replay listing.

import json
import tempfile
from pathlib import Path

import pytest

from nat_mas_agents_v2.models import TaskState
from nat_mas_agents_v2.evaluation import (
    BenchmarkTask,
    load_benchmark_tasks_from_json,
    load_state_from_path,
    list_state_snapshots,
    save_state_to_path,
    StepRecord,
)


def test_benchmark_task_to_initial_state():
    task = BenchmarkTask(
        task_id="t1",
        objective="Create hello.txt",
        repo_root="/tmp/repo",
    )
    state = task.to_initial_state()
    assert state.objective == "Create hello.txt"
    assert state.repo_root == "/tmp/repo"
    assert state.status == "pending"
    assert state.subtasks == []


def test_save_and_load_state(tmp_path: Path):
    state = TaskState(objective="test", repo_root=".")
    out = tmp_path / "state.json"
    save_state_to_path(state, out)
    assert out.exists()
    loaded = load_state_from_path(out)
    assert loaded.objective == state.objective
    assert loaded.repo_root == state.repo_root


def test_step_record():
    state = TaskState(objective="x", repo_root=".")
    rec = StepRecord(step="planner", iteration=0, state=state)
    assert rec.step == "planner"
    assert rec.iteration == 0
    assert rec.state.objective == "x"


def test_list_state_snapshots_empty(tmp_path: Path):
    assert list_state_snapshots(tmp_path) == []


def test_list_state_snapshots_sorted(tmp_path: Path):
    (tmp_path / "iter_001_planner.json").write_text("{}")
    (tmp_path / "iter_000_critic.json").write_text("{}")
    (tmp_path / "iter_001_worker.json").write_text("{}")
    state = TaskState(objective="x", repo_root=".")
    for p in tmp_path.glob("*.json"):
        save_state_to_path(state, p)
    snapshots = list_state_snapshots(tmp_path)
    assert len(snapshots) == 3
    assert snapshots[0][0] == 0 and snapshots[0][1] == "critic"
    assert snapshots[1][0] == 1 and snapshots[1][1] == "planner"
    assert snapshots[2][0] == 1 and snapshots[2][1] == "worker"


def test_load_benchmark_tasks_from_json(tmp_path: Path):
    path = tmp_path / "tasks.json"
    path.write_text(
        json.dumps([
            {"task_id": "a", "objective": "Do A", "repo_root": "."},
            {"task_id": "b", "objective": "Do B", "expect_success": False},
        ])
    )
    tasks = load_benchmark_tasks_from_json(path)
    assert len(tasks) == 2
    assert tasks[0].task_id == "a" and tasks[0].expect_success is True
    assert tasks[1].task_id == "b" and tasks[1].expect_success is False
    assert tasks[1].repo_root == "."
