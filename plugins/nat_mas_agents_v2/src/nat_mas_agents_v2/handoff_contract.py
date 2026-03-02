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

"""Handoff contract: what each agent READS from and WRITES to TaskState.

This is the single source of truth for agent I/O. Ensures coherence:
downstream agents know exactly which fields are populated by whom.
"""

from typing import List

# --- Contract: Agent name -> (fields READ, fields WRITTEN) ---
# READ = fields the agent may read to produce its output
# WRITE = fields the agent is allowed to update (all other fields preserved)

PRODUCT_AGENT_READ: List[str] = ["objective"]
PRODUCT_AGENT_WRITE: List[str] = ["requirement_doc", "updated_at"]

ARCHITECT_AGENT_READ: List[str] = ["objective", "requirement_doc"]
ARCHITECT_AGENT_WRITE: List[str] = ["design_spec", "updated_at"]

PLANNER_AGENT_READ: List[str] = [
    "objective",
    "requirement_doc",
    "design_spec",
    "subtasks",
    "current_subtask_index",
    "critique_history",
    "last_tests",
    "execution_log",
]
PLANNER_AGENT_WRITE: List[str] = [
    "subtasks",
    "current_subtask_index",
    "iteration",
    "status",
    "updated_at",
]

WORKER_AGENT_READ: List[str] = [
    "objective",
    "requirement_doc",
    "design_spec",
    "subtasks",
    "current_subtask_index",
    "artifacts",
    "critique_history",
    "repo_root",
    "subtask_retry_count",
    "max_retries_per_subtask",
    "backup_dir",
]
WORKER_AGENT_WRITE: List[str] = [
    "subtasks",
    "artifacts",
    "subtask_retry_count",
    "updated_at",
]

EXECUTOR_AGENT_READ: List[str] = ["repo_root", "execution_log", "last_tests"]
EXECUTOR_AGENT_WRITE: List[str] = ["execution_log", "last_tests", "updated_at"]

CRITIC_AGENT_READ: List[str] = [
    "iteration",
    "last_tests",
    "execution_log",
    "artifacts",
    "subtasks",
    "current_subtask_index",
]
CRITIC_AGENT_WRITE: List[str] = ["critique_history", "status", "updated_at"]


def get_handoff_contract_doc() -> str:
    """Return a human-readable handoff contract for documentation or prompts."""
    return """
=== HANDOFF CONTRACT (TaskState fields) ===
Product:   READ objective                    → WRITE requirement_doc
Architect: READ objective, requirement_doc  → WRITE design_spec
Planner:   READ objective, requirement_doc, design_spec, subtasks, critique_history, last_tests, execution_log
           → WRITE subtasks, current_subtask_index, iteration, status
Worker:    READ objective, requirement_doc, design_spec, subtasks, current_subtask_index, artifacts, critique_history, repo_root
           → WRITE subtasks, artifacts, subtask_retry_count
Executor:  READ repo_root, execution_log    → WRITE execution_log, last_tests
Critic:    READ iteration, last_tests, execution_log, artifacts, subtasks
           → WRITE critique_history, status
=== END HANDOFF CONTRACT ===
""".strip()
