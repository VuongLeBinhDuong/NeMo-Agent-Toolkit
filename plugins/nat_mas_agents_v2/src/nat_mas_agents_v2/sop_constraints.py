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

"""SOP (Standard Operating Procedures) constraints for MAS V2 software development.

These constraints ensure coherence: all agents follow the same rules for handoff,
output shape, and behavior. Reference these in prompt templates.
"""

# --- Global MAS constraints (inject into agent prompts as needed) ---

STATE_ONLY_HANDOFF = """
HANDOFF CONTRACT: You only read from and write to TaskState. Do not pass information via free text or out-of-band messages. Your output is written to the designated state fields only.
"""

ACCEPTANCE_CRITERIA_SOP = """
ACCEPTANCE CRITERIA: Every acceptance criterion must be testable (e.g. "User can add a todo item", "File X exists and contains Y"). Avoid vague criteria. Prefer observable outcomes.
"""

DESIGN_FOLLOW_SOP = """
DESIGN SPEC: When design_spec is present, Planner MUST align subtasks with its file structure and implementation order. Worker MUST produce one file per subtask; target_files in the current subtask define the file to edit.
"""

ONE_FILE_PER_STEP_SOP = """
WORKER CONSTRAINT: Output exactly one file edit per step: file_path (relative to repo_root or absolute) and complete file content. Do not batch multiple files in one response.
"""

CRITIC_EVIDENCE_SOP = """
CRITIC CONSTRAINT: Verdict (continue | success | fatal_error) MUST be derived only from execution_log and last_tests. Do not speculate. Set root_cause and suggested_fix from actual stderr/stdout and test details.
"""


def get_sop_summary() -> str:
    """Return a concise summary of all SOPs for inclusion in agent system prompts."""
    return (
        "=== MAS V2 SOP (Standard Operating Procedures) ===\n"
        "1. STATE_ONLY: All handoff via TaskState; no free-text pass-through.\n"
        "2. ACCEPTANCE_CRITERIA: Must be testable and observable.\n"
        "3. DESIGN_SPEC: Planner and Worker follow design_spec file structure and order.\n"
        "4. WORKER: One file per step; output file_path + full content.\n"
        "5. CRITIC: Verdict only from execution_log and last_tests; no speculation.\n"
        "=== END SOP ==="
    )


def get_sop_for_agent(agent_name: str) -> str:
    """Return SOP text relevant to a specific agent (for prompt injection)."""
    mapping = {
        "product": STATE_ONLY_HANDOFF.strip() + "\n" + ACCEPTANCE_CRITERIA_SOP.strip(),
        "architect": STATE_ONLY_HANDOFF.strip() + "\n" + DESIGN_FOLLOW_SOP.strip(),
        "planner": STATE_ONLY_HANDOFF.strip() + "\n" + DESIGN_FOLLOW_SOP.strip(),
        "worker": STATE_ONLY_HANDOFF.strip() + "\n" + ONE_FILE_PER_STEP_SOP.strip(),
        "critic": STATE_ONLY_HANDOFF.strip() + "\n" + CRITIC_EVIDENCE_SOP.strip(),
    }
    return mapping.get(agent_name.lower(), get_sop_summary())
