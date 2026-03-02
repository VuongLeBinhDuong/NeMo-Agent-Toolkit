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

"""Structured output schemas for all MAS V2 agents.

Single source of truth for LLM output shape. Each agent uses one of these
via with_structured_output(schema). Ensures coherence and parseability.
"""

from typing import List

from pydantic import BaseModel, Field


# --- Product Agent ---
class RequirementDocOutput(BaseModel):
    """Structured output from Product Agent: PRD and acceptance criteria."""

    summary: str = Field(
        description="Short summary of the clarified requirement (1-3 sentences)",
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of concrete, testable acceptance criteria",
    )
    scope: str = Field(
        default="",
        description="Optional scope or out-of-scope notes",
    )


# --- Architect Agent ---
class DesignSpecOutput(BaseModel):
    """Structured output from Architect Agent: file structure, modules, API, per-file requirements."""

    file_structure: List[str] = Field(
        default_factory=list,
        description="List ALL file paths to create: every HTML page, CSS, and JS (e.g. index.html, shop.html, product-detail.html, cart.html, styles.css, app.js). Do not limit to 3 files.",
    )
    file_requirements: str = Field(
        default="",
        description="Per-file requirements: for EACH file in file_structure, one line 'filename: requirements'. Example: 'index.html: Shared header and footer, hero section, featured product grid; link styles.css and script.js; semantic HTML5; meta description and viewport; no inline CSS/JS.' Be specific so a developer can implement production-quality code from this.",
    )
    modules: str = Field(
        default="",
        description="Short description of modules/components and their responsibilities",
    )
    api_or_contracts: str = Field(
        default="",
        description="API endpoints, data contracts, or interfaces if applicable",
    )
    implementation_notes: str = Field(
        default="",
        description="Optional implementation order or technical notes",
    )


# --- Planner Agent ---
class SubtaskPlanItem(BaseModel):
    """One subtask as produced by the Planner LLM."""

    id: str = Field(description="Short unique id, e.g. '1', '2', 'fix-tests'")
    description: str = Field(description="Clear description of what to do")
    target_files: List[str] = Field(
        default_factory=list,
        description="File paths this subtask will touch (relative to repo_root)",
    )
    notes: str = Field(
        default="",
        description="Optional context or constraints",
    )


class PlannerOutput(BaseModel):
    """Structured output from the Planner LLM: incremental subtasks."""

    subtasks: List[SubtaskPlanItem] = Field(
        description="Ordered list of subtasks (incremental decomposition or refinement)",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for this plan (for logging)",
    )


# --- Worker Agent ---
class CodeEditOutput(BaseModel):
    """Structured output from Worker: one file path and full content."""

    file_path: str = Field(
        description="Relative path from repo_root or absolute path"
    )
    content: str = Field(description="Complete file content to write")
