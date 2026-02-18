# MAS V2 Reliability & Robustness Layer

Mechanisms to keep the agent loop from failing unpredictably and to recover or report partial results.

## 1. Retry worker when patch fails

- **Worker** increments `subtask_retry_count[subtask_id]` when:
  - LLM structured output fails (exception or empty file_path/content)
  - `write_file` (patch) fails
- The same subtask is retried on the **next iteration** (planner → worker → …).
- **Limit**: `max_retries_per_subtask` (default `2`) in `TaskState`. If retries exceed this, the worker marks the subtask **blocked** and skips work for it.

**Config**: Set `TaskState.max_retries_per_subtask` (e.g. in initial state or via workflow).

## 2. Rollback code when tests fail badly

- When **Critic** sets `status = "failed"` (e.g. verdict `fatal_error`), the workflow can **restore** files from backup.
- **Backup**: If `TaskState.backup_dir` is set, the worker backs up the **current file content** to `backup_dir` before each write (overwrites previous backup for that path).
- **Restore**: After critic returns failed, the workflow calls `restore_from_backup(backup_dir, repo_root)` so the repo is rolled back to the last backed-up state.

**Usage**: Set `initial_state.backup_dir` to a directory path (e.g. `runs/run_001/backups`) when you want rollback on fatal.

## 3. Limit retries per subtask

- `TaskState.subtask_retry_count: Dict[str, int]` stores retries per subtask id.
- `TaskState.max_retries_per_subtask` (default `2`) is the cap.
- When the worker sees `retry_count > max_retries_per_subtask`, it marks the current subtask as **blocked** and returns without applying a patch.

## 4. Detect loop / stuck state

- **Stuck** = last `stuck_window` (default `3`) critiques all have `verdict == "continue"` (no success, no fatal).
- The workflow uses `is_stuck(state, window=config.stuck_window)`. When stuck is detected, it sets `status = "failed"` and exits the loop (then partial success may still be applied if there was progress).

**Config**: `CodeLoopWorkflowConfig.stuck_window` (default `3`).

## 5. Partial success handling

- When the loop ends with `status == "failed"` but `state.has_partial_progress()` is true (there are **artifacts** or **done subtasks**), the workflow sets `status = "partial_success"`.
- Callers can treat `partial_success` as “some deliverables, but not all” and e.g. save what was produced or retry with a different strategy.

**Status values**: `pending` | `in_progress` | `success` | `failed` | `partial_success`.

---

## TaskState fields (reliability)

| Field | Default | Description |
|-------|---------|-------------|
| `subtask_retry_count` | `{}` | Per-subtask retry count (worker updates). |
| `max_retries_per_subtask` | `2` | Max retries before marking subtask blocked. |
| `backup_dir` | `None` | If set, worker backs up before write; workflow restores on fatal. |
| `status` | … | Can be `partial_success` when failed but has partial progress. |

## Workflow config (reliability)

| Field | Default | Description |
|-------|---------|-------------|
| `stuck_window` | `3` | Number of consecutive "continue" verdicts to consider stuck. |

## Enabling in YAML

Example initial state (when using evaluation harness or custom entry):

```yaml
# In code that builds initial TaskState:
# backup_dir: "runs/run_001/backups"   # enable rollback on fatal
# max_retries_per_subtask: 2
```

Workflow YAML:

```yaml
workflow:
  _type: nat_mas_agents_v2/code_loop_workflow
  planner: planner_step
  worker: worker_step
  executor: executor_step
  critic: critic_step
  max_iterations: 15
  stuck_window: 3
```
