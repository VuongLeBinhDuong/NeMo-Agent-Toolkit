# MAS V2 Evaluation and Testing Harness

System to measure agent quality, run regression tests, log state per iteration, and replay failed runs for production stability.

## Overview

| Component | Purpose |
|-----------|--------|
| **State logging** | Run the code loop and log `TaskState` after every step (planner → worker → executor → critic) to JSON. |
| **Benchmark** | Run defined tasks, collect metrics (success, iterations, duration, artifacts, critiques), write summary. |
| **Replay** | Load a saved state from a past run and re-run from that point (e.g. after fixing a bug). |
| **Regression tests** | Pytest tests that assert invariants and, with full NAT config, run benchmark tasks. |

## 1. Logging state each iteration

Use `run_workflow_with_logging` instead of the registered `code_loop_workflow` when you need step-by-step state dumps:

```python
from pathlib import Path
from nat_mas_agents_v2.evaluation import run_workflow_with_logging
from nat_mas_agents_v2.models import TaskState

# builder from your NAT workflow config (YAML)
initial_state = TaskState(objective="Create hello.txt", repo_root=".")
final_state, records = await run_workflow_with_logging(
    builder,
    planner=FunctionRef(name="planner_step"),
    worker=FunctionRef(name="worker_step"),
    executor=FunctionRef(name="executor_step"),
    critic=FunctionRef(name="critic_step"),
    initial_state=initial_state,
    max_iterations=15,
    log_dir=Path("runs/run_001"),
)
# log_dir will contain iter_000_planner.json, iter_000_worker.json, ...
```

Each `StepRecord` has `step`, `iteration`, and `state` (and optionally `state_json` when using `log_dir`).

## 2. Task benchmark

Define tasks in JSON (e.g. `evaluation/benchmark_tasks/example_tasks.json`):

```json
[
  {
    "task_id": "simple_hello",
    "objective": "Create hello.txt with content 'Hello, MAS'",
    "repo_root": ".",
    "expect_success": true
  }
]
```

Run a single task or a suite:

```python
from nat_mas_agents_v2.evaluation import (
    BenchmarkTask,
    run_benchmark_task,
    run_benchmark_suite,
    load_benchmark_tasks_from_json,
)

task = BenchmarkTask(task_id="t1", objective="Create README", repo_root=".")
result = await run_benchmark_task(
    builder, task,
    planner=..., worker=..., executor=..., critic=...,
    log_dir=Path("runs/t1"),
)
assert result.success == task.expect_success  # regression

# Or run many tasks and write benchmark_summary.json
tasks = load_benchmark_tasks_from_json(Path("benchmark_tasks/example_tasks.json"))
results = await run_benchmark_suite(
    builder, tasks,
    planner=..., worker=..., executor=..., critic=...,
    output_dir=Path("benchmark_out"),
)
```

`BenchmarkResult` includes: `success`, `status`, `iterations`, `duration_seconds`, `num_subtasks`, `num_artifacts`, `num_critiques`, `log_dir`, `error`.

## 3. Replay failed runs

From a run that wrote state snapshots to `log_dir`:

```python
from nat_mas_agents_v2.evaluation import (
    replay_from_log_dir,
    load_latest_state,
    load_state_at_iteration,
    list_state_snapshots,
)

# List all saved snapshots (iter_000_planner.json, ...)
snapshots = list_state_snapshots(Path("runs/run_001"))

# Load latest state (end of last step)
state = load_latest_state(Path("runs/run_001"))

# Load state at end of iteration 2 (after critic)
state = load_state_at_iteration(Path("runs/run_001"), iteration=2, after_step="critic")

# Re-run from that state (e.g. after fixing code)
final = await replay_from_log_dir(
    builder, Path("runs/run_001"),
    planner=..., worker=..., executor=..., critic=...,
    from_iteration=2,  # or None to use latest
    output_log_dir=Path("runs/run_001_replay"),
)
```

## 4. Regression tests

- **tests/test_evaluation_harness.py**: Unit tests for `BenchmarkTask`, save/load state, `StepRecord`, `list_state_snapshots`, `load_benchmark_tasks_from_json`.
- **tests/test_mas_regression.py**: Invariants on initial state, `BenchmarkResult` serialization, replay helpers on saved state; optional full workflow run (mark as integration if needed).

Run from repo root (with plugin installed):

```bash
pytest plugins/nat_mas_agents_v2/tests -v
```

Or with asyncio:

```bash
pytest plugins/nat_mas_agents_v2/tests -v -p pytest_asyncio
```

## Production checklist

- Run benchmark suite before releases and assert `result.success == task.expect_success` for each task.
- Enable state logging for critical or failing runs; use `log_dir` and keep runs for replay.
- Use replay to reproduce and fix failures without re-running from scratch.
- Add new benchmark tasks for new behaviors you want to guard against regressions.
