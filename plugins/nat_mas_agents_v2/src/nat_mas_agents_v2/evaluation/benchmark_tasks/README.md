# Benchmark tasks

Place benchmark task definitions here as JSON files. Format:

```json
[
  {
    "task_id": "unique_id",
    "objective": "Human-readable task for the MAS",
    "repo_root": ".",
    "expect_success": true
  }
]
```

- `task_id`: Used for log subdirs and reporting.
- `objective`: Passed to `TaskState.objective`.
- `repo_root`: Passed to `TaskState.repo_root` (default `"."`).
- `expect_success`: For regression: assert `result.success == expect_success`.

Load with `load_benchmark_tasks_from_json(path)` from `nat_mas_agents_v2.evaluation`.
