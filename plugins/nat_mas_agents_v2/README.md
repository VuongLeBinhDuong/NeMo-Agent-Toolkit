# NAT MAS Agents V2

Tool-grounded iterative coding loop architecture with structured shared state communication.

## Architecture Overview

This package implements a minimal agent loop consisting of:

1. **Planner** - Progressive task decomposition (not full upfront planning)
2. **Worker/Coder** - Code generation with tool usage (file operations, repo navigation)
3. **Executor** - Runtime execution and test running
4. **Critic/Verifier** - Analyzing runtime logs, test results, and diffs, then triggering refinement loops

## Key Design Principles

### 1. Structured Shared State (TaskState)

**Golden Rule**: Agents do NOT pass information via prompt text. They only read/write state.

All agents operate on a single `TaskState` object that contains:
- `objective` - High-level goal
- `subtasks` - Progressive task decomposition
- `current_subtask` - Focused work item
- `artifacts` - File metadata (not content)
- `execution_logs` - Test/build/lint results
- `test_results` - Structured test outcomes
- `critique_history` - Feedback from Critic
- `iteration_count` - Loop counter
- `status` - Overall task status

### 2. Tool-Grounded Reasoning

- Heavy reliance on code execution, static analysis, and test harness integration
- Worker uses file operations and repo navigation tools
- Executor runs actual tests and captures results
- Critic analyzes objective verification signals (not speculation)

### 3. Iterative Generate → Execute → Critique → Regenerate

The workflow loops until:
- `status == "success"` (objective achieved)
- `status == "failed"` (fatal error)
- `critique.verdict == "fatal_error"` (unrecoverable issue)
- Maximum iterations reached

## Usage Example

```python
from nat_mas_agents_v2.models import TaskState

# Initialize state
state = TaskState(
    objective="Create a simple todo app with add/delete functionality",
    repo_root=".",
)

# Planner adds subtasks
state.subtasks = [
    Subtask(
        id="1",
        description="Create HTML structure with input and list",
        target_files=["index.html"],
    ),
    Subtask(
        id="2",
        description="Add JavaScript for add/delete functionality",
        target_files=["script.js"],
    ),
]

# Worker processes current subtask
state.current_subtask_index = 0
current = state.get_current_subtask()

# Executor runs tests
state.execution_log.append(
    ExecutionLog(
        step="pytest",
        command="pytest tests/",
        exit_code=0,
        stdout="1 passed",
    )
)

# Critic provides feedback
state.critique_history.append(
    Critique(
        iteration=1,
        verdict="continue",
        reasons=["Tests pass but UI needs styling"],
        suggested_changes=["Add CSS file"],
    )
)
```

## Models

- `TaskState` - Main shared state container
- `Subtask` - Individual task items
- `ArtifactMetadata` - File metadata tracking
- `ExecutionLog` - Execution step logs
- `TestResult` - Structured test results
- `Critique` - Feedback from Critic

See `models.py` for full documentation.

## Workflow YAML Example

```yaml
functions:
  planner_step:
    _type: nat_mas_agents_v2/planner_step
    llm_name: reasoning_llm
  worker_step:
    _type: nat_mas_agents_v2/worker_step
    llm_name: code_generation_llm
  executor_step:
    _type: nat_mas_agents_v2/executor_step
  critic_step:
    _type: nat_mas_agents_v2/critic_step
  list_files:
    _type: nat_mas_agents_v2/list_files
  read_file:
    _type: nat_mas_agents_v2/read_file
  write_file:
    _type: nat_mas_agents_v2/write_file
  run_shell:
    _type: nat_mas_agents_v2/run_shell
  run_test:
    _type: nat_mas_agents_v2/run_test

  code_loop_workflow:
    _type: nat_mas_agents_v2/code_loop_workflow
    planner: planner_step
    worker: worker_step
    executor: executor_step
    critic: critic_step
    max_iterations: 15

workflow:
  _type: nat_mas_agents_v2/code_loop_workflow
```

Invoke with initial `TaskState` (e.g. `objective` and `repo_root` set, `status: "in_progress"`). The workflow returns the final `TaskState` when `status` is `success` or `failed` or when `max_iterations` is reached.
