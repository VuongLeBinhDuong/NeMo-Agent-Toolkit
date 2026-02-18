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

"""Shared Task State models for MAS V2 workflow.

This module defines the structured state schema that all agents (Planner, Worker,
Executor, Critic) read from and write to. This eliminates free-text inter-agent
communication and ensures type-safe, structured data flow.

Key principle: Agents do NOT pass information via prompt text. They only read/write state.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class Subtask(BaseModel):
    """Represents a single subtask in the task decomposition.

    Subtasks are created by the Planner and executed by the Worker.
    They represent incremental, focused coding tasks rather than full upfront planning.
    """

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this subtask",
    )
    description: str = Field(
        description="Human-readable description of what needs to be done"
    )
    status: Literal["pending", "in_progress", "done", "blocked"] = Field(
        default="pending",
        description="Current status of the subtask",
    )
    target_files: List[str] = Field(
        default_factory=list,
        description="List of file paths that this subtask will modify or create",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes or context for this subtask",
    )


class ArtifactMetadata(BaseModel):
    """Metadata about a generated artifact (file).

    Note: This stores metadata only, not file content. File content should be
    read via file_reader tool when needed.
    """

    path: str = Field(description="Relative path to the artifact file")
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when artifact was created",
    )
    modified_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when artifact was last modified",
    )
    checksum: Optional[str] = Field(
        default=None,
        description="Optional checksum/hash to detect changes",
    )
    status: Literal["draft", "tested", "approved"] = Field(
        default="draft",
        description="Current status of the artifact",
    )


class ExecutionLog(BaseModel):
    """Log entry for a single execution step (test run, lint, build, etc.).

    These logs are used by the Critic to analyze failures and provide feedback.
    """

    step: str = Field(
        description="Name of the execution step (e.g., 'pytest', 'lint', 'build')"
    )
    command: str = Field(description="Command that was executed")
    exit_code: int = Field(description="Exit code of the command (0 = success)")
    stdout: str = Field(
        default="",
        description="Standard output from the command",
    )
    stderr: str = Field(
        default="",
        description="Standard error output from the command",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when execution occurred",
    )


class TestResult(BaseModel):
    """Results from test execution.

    This provides structured test results that the Critic can analyze
    to determine if code changes are successful.
    """

    passed: int = Field(
        default=0,
        ge=0,
        description="Number of tests that passed",
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Number of tests that failed",
    )
    errors: int = Field(
        default=0,
        ge=0,
        description="Number of test errors",
    )
    skipped: int = Field(
        default=0,
        ge=0,
        description="Number of tests that were skipped",
    )
    details: str = Field(
        default="",
        description="Detailed test output or summary (machine-parsable format preferred)",
    )


class Critique(BaseModel):
    """Feedback from the Critic agent after analyzing execution results.

    This drives the iterative refinement loop by providing structured feedback
    on what needs to be fixed or improved. Structured fields support downstream
    tools (Planner/Worker) with root_cause, affected_files, suggested_fix, confidence.
    """

    iteration: int = Field(
        ge=0,
        description="Iteration number when this critique was generated",
    )
    verdict: Literal["continue", "success", "fatal_error"] = Field(
        description="Overall verdict: continue refining, success achieved, or fatal error"
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="List of reasons explaining the verdict",
    )
    suggested_changes: List[str] = Field(
        default_factory=list,
        description="Specific suggestions for what should be changed in the next iteration",
    )
    blocking_issues: List[str] = Field(
        default_factory=list,
        description="Critical issues that must be resolved before proceeding",
    )
    # Structured feedback for Planner/Worker
    root_cause: str = Field(
        default="",
        description="Identified root cause of failure or success summary",
    )
    affected_files: List[str] = Field(
        default_factory=list,
        description="File paths likely affected by the issue or touched in this iteration",
    )
    suggested_fix: str = Field(
        default="",
        description="Concrete suggested fix (e.g. change X in file Y)",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this critique (0-1); higher when based on clear logs/tests",
    )


class TaskState(BaseModel):
    """Global shared state for the MAS V2 workflow.

    This is the single source of truth that all agents (Planner, Worker, Executor, Critic)
    read from and write to. It eliminates free-text handoffs and ensures structured
    communication.

    Key principles:
    - Agents only read/write this state, never pass information via prompts
    - State is immutable-friendly: each agent creates a new state or copies before modifying
    - File content is NOT stored in state (use file_reader tool when needed)
    - State can be persisted to JSON for resuming tasks
    """

    # Core task information
    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this task",
    )
    objective: str = Field(
        description="High-level objective/goal of the task"
    )
    repo_root: str = Field(
        default=".",
        description="Root directory of the repository/project",
    )
    status: Literal["pending", "in_progress", "success", "failed", "partial_success"] = Field(
        default="pending",
        description="Overall status of the task (partial_success = some work done but failed to complete)",
    )
    iteration: int = Field(
        default=0,
        ge=0,
        description="Current iteration number in the refinement loop",
    )

    # Reliability: retry and rollback
    subtask_retry_count: Dict[str, int] = Field(
        default_factory=dict,
        description="Per-subtask retry count (subtask_id -> count) for worker patch failures",
    )
    max_retries_per_subtask: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Max retries for worker on same subtask before marking blocked",
    )
    backup_dir: Optional[str] = Field(
        default=None,
        description="If set, worker backs up file before write; workflow restores from here on fatal",
    )

    # Task decomposition (managed by Planner)
    subtasks: List[Subtask] = Field(
        default_factory=list,
        description="List of subtasks decomposed from the objective",
    )
    current_subtask_index: Optional[int] = Field(
        default=None,
        description="Index of the current subtask being worked on (None if no subtask selected)",
    )

    # Artifacts tracking (managed by Worker)
    artifacts: Dict[str, ArtifactMetadata] = Field(
        default_factory=dict,
        description="Map of file path -> artifact metadata (does not contain file content)",
    )

    # Execution logs (managed by Executor)
    execution_log: List[ExecutionLog] = Field(
        default_factory=list,
        description="History of all execution steps (tests, lint, build, etc.)",
    )
    last_tests: Optional[TestResult] = Field(
        default=None,
        description="Results from the most recent test execution",
    )

    # Feedback loop (managed by Critic)
    critique_history: List[Critique] = Field(
        default_factory=list,
        description="History of critiques from the Critic agent",
    )

    # Metadata
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when task was created",
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="ISO timestamp when task state was last updated",
    )

    @field_validator("current_subtask_index")
    @classmethod
    def validate_subtask_index(cls, v: Optional[int], info) -> Optional[int]:
        """Validate that current_subtask_index is within bounds of subtasks list."""
        if v is None:
            return v
        if "subtasks" in info.data:
            subtasks = info.data["subtasks"]
            if not isinstance(subtasks, list):
                return v
            if v < 0 or v >= len(subtasks):
                raise ValueError(
                    f"current_subtask_index {v} is out of bounds for subtasks list of length {len(subtasks)}"
                )
        return v

    @model_validator(mode="after")
    def update_timestamp(self) -> "TaskState":
        """Automatically update updated_at timestamp when state is modified."""
        self.updated_at = datetime.now().isoformat()
        return self

    def get_current_subtask(self) -> Optional[Subtask]:
        """Get the current subtask being worked on.

        Returns:
            Current Subtask if one is selected, None otherwise.
        """
        if self.current_subtask_index is None:
            return None
        if (
            self.current_subtask_index < 0
            or self.current_subtask_index >= len(self.subtasks)
        ):
            return None
        return self.subtasks[self.current_subtask_index]

    def get_latest_critique(self) -> Optional[Critique]:
        """Get the most recent critique from the Critic.

        Returns:
            Latest Critique if available, None otherwise.
        """
        if not self.critique_history:
            return None
        return self.critique_history[-1]

    def is_success(self) -> bool:
        """Check if task has achieved success status.

        Returns:
            True if status is 'success', False otherwise.
        """
        return self.status == "success"

    def should_continue(self) -> bool:
        """Check if workflow should continue iterating.

        Returns:
            True if status is 'in_progress' and no fatal error, False otherwise.
        """
        if self.status in ("failed", "success", "partial_success"):
            return False
        latest = self.get_latest_critique()
        if latest and latest.verdict == "fatal_error":
            return False
        return True

    def has_partial_progress(self) -> bool:
        """True if there are done subtasks or artifacts (for partial_success handling)."""
        if self.artifacts:
            return True
        return any(s.status == "done" for s in self.subtasks)

    def to_dict(self) -> dict:
        """Convert TaskState to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the state.
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict) -> "TaskState":
        """Create TaskState from dictionary (e.g., loaded from JSON).

        Args:
            data: Dictionary containing state data.

        Returns:
            TaskState instance.
        """
        return cls(**data)
