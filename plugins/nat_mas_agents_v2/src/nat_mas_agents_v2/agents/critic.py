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

"""Critic agent: analyze execution_log and last_tests; produce structured Critique.

SOP: Verdict (continue | success | fatal_error) MUST be derived only from
execution_log and last_tests. See sop_constraints.CRITIC_EVIDENCE_SOP and
handoff_contract.CRITIC_AGENT_READ/WRITE.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

from ..models import Critique, Subtask, TaskState

log = logging.getLogger(__name__)


def _parse_affected_files_from_log(stderr: str, stdout: str) -> List[str]:
    """Extract file paths from stderr/stdout (e.g. file.py:line or path/to/file.py)."""
    combined = f"{stderr}\n{stdout}"
    pattern = r"[a-zA-Z0-9_./\\-]+\.(?:py|js|ts|tsx|yaml|yml|json|md)(?::\d+)?"
    found = re.findall(pattern, combined)
    seen = set()
    out = []
    for p in found:
        base = p.split(":")[0] if ":" in p else p
        if base not in seen and len(base) > 1:
            seen.add(base)
            out.append(base)
    return out[:20]


class CriticStepConfig(FunctionBaseConfig, name="critic_step"):
    """Configuration for the Critic step."""

    description: str = Field(
        default="Analyze execution_log and last_tests; produce structured Critique (root_cause, affected_files, suggested_fix, confidence).",
        description="Description of the critic step",
    )


@register_function(config_type=CriticStepConfig)
async def critic_step(config: CriticStepConfig, builder: Builder):
    """Critic step: analyze results and append structured critique; set status on success/fatal."""

    log.info("Initializing critic_step")

    def _extract_file_structure(design_spec: str | None) -> List[str]:
        """Parse design_spec text to recover the File Structure list (same format as Architect/Planner)."""
        if not design_spec:
            return []
        lines = design_spec.splitlines()
        files: List[str] = []
        in_fs = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## ") and "File Structure" in stripped:
                in_fs = True
                continue
            if in_fs:
                # stop when the next section starts
                if stripped.startswith("## "):
                    break
                if stripped.startswith("- "):
                    name = stripped[2:].strip()
                    if name:
                        files.append(name)
        return files

    async def _critic(state: TaskState) -> TaskState:
        state = state.model_copy(deep=True)
        iteration = state.iteration
        reasons = []
        suggested_changes = []
        blocking_issues = []
        root_cause = ""
        affected_files: List[str] = []
        suggested_fix = ""
        confidence = 0.0

        if state.last_tests:
            t = state.last_tests
            if t.failed > 0 or t.errors > 0:
                reasons.append(f"Tests: {t.passed} passed, {t.failed} failed, {t.errors} errors.")
                suggested_changes.append("Fix failing tests before proceeding.")
                root_cause = f"Test failures: {t.failed} failed, {t.errors} errors. Details: {(t.details or '')[:500]}"
                suggested_fix = "Fix failing tests; check test output and adjust code under test."
                confidence = 0.8 if t.details else 0.5
            else:
                reasons.append(f"All tests passed ({t.passed} passed).")
                root_cause = "All tests passed."
                suggested_fix = ""
                confidence = 0.9
        else:
            reasons.append("No test results in state.")
            root_cause = "No test results available."
            confidence = 0.2

        if state.execution_log:
            last_log = state.execution_log[-1]
            if last_log.exit_code != 0:
                blocking_issues.append(f"Last step '{last_log.step}' exited with code {last_log.exit_code}.")
                if last_log.stderr:
                    reasons.append(f"Stderr: {last_log.stderr[:200]}")
                    if not root_cause:
                        root_cause = last_log.stderr[:500].strip() or f"Step '{last_log.step}' failed with exit code {last_log.exit_code}."
                    suggested_fix = "Address stderr output and fix the failing step."
                    confidence = max(confidence, 0.7)
                affected_files = _parse_affected_files_from_log(last_log.stderr or "", last_log.stdout or "")
            if last_log.stderr and not affected_files:
                affected_files = _parse_affected_files_from_log(last_log.stderr, last_log.stdout)

        if not affected_files and state.artifacts:
            affected_files = list(state.artifacts.keys())[:10]
        current = state.get_current_subtask()
        if not affected_files and current and current.target_files:
            affected_files = list(current.target_files)[:10]

        tests_ok = bool(state.last_tests and state.last_tests.failed == 0 and state.last_tests.errors == 0)
        remaining_subtasks = [s for s in (state.subtasks or []) if s.status != "done"]

        # Additionally require that all files listed in the Design Spec File Structure
        # actually exist on disk or in artifacts (defensive against Planner marking
        # subtasks as done without Worker ever running them).
        expected_files = _extract_file_structure(state.design_spec)
        missing_files: List[str] = []
        if expected_files:
            # Build a lookup set of artifact basenames (e.g. index.html, products.json)
            artifact_names: set[str] = set()
            for key in (state.artifacts or {}).keys():
                # keys look like "output\\index.html"
                base = str(key).replace("\\", "/").split("/")[-1]
                if base:
                    artifact_names.add(base.lower())

            repo_root = Path(state.repo_root or ".").resolve()
            output_dir = str(state.output_dir or "").strip() or "."
            out_base = (repo_root / output_dir).resolve()

            for fname in expected_files:
                raw = (fname or "").strip()
                if not raw:
                    continue
                base = raw.replace("\\", "/").split("/")[-1]
                base_lower = base.lower()
                exists_in_artifacts = base_lower in artifact_names
                exists_on_disk = (out_base / base).exists()
                if not (exists_in_artifacts or exists_on_disk):
                    missing_files.append(base)

        if missing_files:
            reasons.append(
                f"Design spec File Structure includes files that are missing on disk/artifacts: {missing_files}."
            )
            # Đảm bảo luôn có ít nhất một subtask cho mỗi file còn thiếu,
            # để vòng lặp Planner → Worker bắt buộc tạo chúng (products.json, styles.css, ...).
            existing_targets: set[str] = set()
            for st in state.subtasks or []:
                for path in st.target_files or []:
                    p = (path or "").strip().replace("\\", "/")
                    if "/" in p:
                        p = p.split("/")[-1]
                    if p:
                        existing_targets.add(p.lower())

            new_subtasks = list(state.subtasks or [])
            for fname in missing_files:
                key = (fname or "").strip().replace("\\", "/").split("/")[-1]
                key_lower = key.lower()
                if not key_lower or key_lower in existing_targets:
                    continue
                sub_id = f"CR-{key}"
                new_subtasks.append(
                    Subtask(
                        id=sub_id,
                        description=f"Create or fix {key} exactly according to the Design Spec File Structure and Per-file Requirements.",
                        status="pending",
                        target_files=[key],
                        notes="Auto-added by Critic because file is missing on disk/artifacts.",
                    )
                )
            if new_subtasks:
                state.subtasks = new_subtasks

        # Success yêu cầu:
        # 1) Tests sạch
        # 2) Không còn subtasks pending
        # 3) Không còn file nào trong File Structure bị thiếu (missing_files trống)
        if tests_ok and not remaining_subtasks and not missing_files:
            verdict = "success"
            state.status = "success"
        elif blocking_issues or (state.last_tests and state.last_tests.errors > 0) or (state.last_tests and state.last_tests.failed > 0):
            verdict = "fatal_error"
            state.status = "failed"
        else:
            verdict = "continue"
            # Keep status in_progress so the code loop continues.
            if state.status not in ("pending", "in_progress"):
                state.status = "in_progress"
            if remaining_subtasks:
                reasons.append(f"Pending subtasks remain ({len(remaining_subtasks)}). Continue iteration.")

        critique = Critique(
            iteration=iteration,
            verdict=verdict,
            reasons=reasons,
            suggested_changes=suggested_changes,
            blocking_issues=blocking_issues,
            root_cause=root_cause,
            affected_files=affected_files,
            suggested_fix=suggested_fix,
            confidence=confidence,
        )
        state.critique_history = list(state.critique_history) + [critique]
        state.updated_at = datetime.now().isoformat()

        log.info(
            "Critic: verdict=%s status=%s root_cause=%s affected=%s confidence=%.2f",
            verdict,
            state.status,
            (root_cause or "")[:80],
            len(affected_files),
            confidence,
        )
        return state

    yield FunctionInfo.from_fn(
        _critic,
        input_schema=TaskState,
        description=config.description,
    )
