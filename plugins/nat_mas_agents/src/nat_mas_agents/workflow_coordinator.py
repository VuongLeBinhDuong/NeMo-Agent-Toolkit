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

"""Coordinator that orchestrates the MAS multi-agent workflow via Python."""

import logging
import re
import textwrap
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig
from pydantic import Field

logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "product_manager": "Product specification saved",
    "architect": "Architecture design saved",
    "project_manager": "Project plan saved",
    "engineer": "Code generation completed",
    "tester": "Test report saved",
    "integrator": "Integration summary saved",
}

DOC_VALIDATIONS = {
    "product_manager": {
        "file_path": Path("output/doc/pm_output.txt"),
        "required_sections": [
            "PRODUCT",
            "REQUIREMENTS",
            "FEATURES",
            "PRODUCTS",
            "CATEGORIES",
            "SORT_OPTIONS",
            "FUNCTIONALITY",
            "UI_COMPONENTS",
            "PAGE_REQUIREMENTS",
            "SUCCESS_CRITERIA",
            "SHARED_COMPONENTS",
        ],
    },
    "architect": {
        "file_path": Path("output/doc/architect_output.txt"),
        "required_sections": [
            "REQUIREMENTS",
            "FUNCTIONALITY",
            "UI_COMPONENTS",
            "SHARED_COMPONENTS",
            "SHARED_ASSETS",
            "FILES",
            "ORDER",
            "FILE_REQUIREMENTS",
        ],
    },
    "project_manager": {
        "file_path": Path("output/doc/project_manager_output.txt"),
        "required_sections": [
            "PROJECT_NAME",
            "REQUIREMENTS",
            "SHARED_COMPONENTS",
            "SHARED_ASSETS",
            "FILES",
            "ORDER",
            "FILE_REQUIREMENTS",
            "STEPS",
        ],
    },
    "tester": {
        "file_path": Path("output/doc/tester_output.txt"),
        "required_sections": [
            "PROJECT_NAME",
            "SCOPE",
            "VERIFICATIONS",
            "FINDINGS",
            "PATCHES",
            "RECOMMENDATIONS",
            "SIGN_OFF",
        ],
    },
    "integrator": {
        "file_path": Path("output/doc/integrator_output.txt"),
        "required_sections": [
            "PROJECT_NAME",
            "STATUS_SUMMARY",
            "FIX_HISTORY",
            "QA_STATUS",
            "DELIVERABLES",
            "NEXT_STEPS",
            "SIGN_OFF",
        ],
    },
}


class MASWorkflowConfig(FunctionBaseConfig, name="mas_workflow"):
    """Configuration for the MAS workflow coordinator."""

    product_manager: FunctionRef
    architect: FunctionRef
    project_manager: FunctionRef
    engineer: FunctionRef
    tester: FunctionRef
    integrator: Optional[FunctionRef] = None
    max_fix_iterations: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum number of QA-driven fix attempts after the initial engineer run.",
    )
    require_pass_before_integrator: bool = Field(
        default=True,
        description="If true, integrator phase only runs after QA passes; otherwise it runs regardless.",
    )


def _extract_status(agent_name: str, output_text: str) -> str:
    """Extract STATUS line from an agent's output."""

    for line in output_text.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("STATUS:"):
            status = stripped_line.split("STATUS:", 1)[1].strip()
            if status:
                return status
    json_match = re.search(r'"STATUS"\s*:\s*"([^"]+)"', output_text)
    if json_match:
        return json_match.group(1).strip()
    single_quote_match = re.search(r"'STATUS'\s*:\s*'([^']+)'", output_text)
    if single_quote_match:
        return single_quote_match.group(1).strip()
    recovered_status = _recover_status_from_tool_call(agent_name, output_text)
    if recovered_status:
        return recovered_status
    raise ValueError(f"{agent_name} did not return a STATUS line")


def _recover_status_from_tool_call(agent_name: str, output_text: str) -> str | None:
    """Attempt to recover STATUS by executing the agent's intended tool call."""

    triple_double = re.search(r'"code_content"\s*:\s*"""(.*?)"""', output_text, re.DOTALL)
    triple_single = re.search(r"'code_content'\s*:\s*'''(.*?)'''", output_text, re.DOTALL)
    code_match = triple_double or triple_single
    if not code_match:
        return None

    file_path_match = re.search(r'"file_path"\s*:\s*"([^"]+)"', output_text)
    if not file_path_match:
        file_path_match = re.search(r"'file_path'\s*:\s*'([^']+)'", output_text)
    if not file_path_match:
        return None

    code_content = textwrap.dedent(code_match.group(1))
    normalized_content = (
        code_content.replace("\r\n", "\n")
        .replace("\u2022", "-")
        .replace("•", "-")
        .strip("\n")
    )

    file_path = Path(file_path_match.group(1))
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(f"{normalized_content}\n", encoding="utf-8")

    for expected_status in DEFAULT_AGENT_STATUSES.values():
        if expected_status in output_text:
            status = expected_status
            break
    else:
        status = DEFAULT_AGENT_STATUSES.get(agent_name, "Completed")

    logger.warning(
        "Recovered %s output by writing %s due to missing STATUS line",
        agent_name,
        file_path,
    )
    return status


async def _invoke_agent(
    agent_name: str,
    agent_call: Callable[[str], Awaitable[str]],
    payload: str,
) -> str:
    """Invoke an agent tool and return its string output."""
    start_time = time.time()
    logger.info("Calling %s agent (payload length: %d chars)...", agent_name, len(payload))
    
    try:
        result = await agent_call(payload)
        elapsed_time = time.time() - start_time
        logger.info("%s agent completed in %.2f seconds", agent_name, elapsed_time)
        
        if not isinstance(result, str):
            raise TypeError(f"Expected {agent_name} output to be a string")
        logger.info("%s agent returned output (length: %d chars)", agent_name, len(result))
        return result
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error("%s agent failed after %.2f seconds: %s", agent_name, elapsed_time, e, exc_info=True)
        raise


def _validate_document(agent_name: str):
    """Ensure required sections exist in the agent's saved document."""

    validation = DOC_VALIDATIONS.get(agent_name)
    if not validation:
        return

    file_path: Path = validation["file_path"]
    if not file_path.exists():
        # For tester phase, be more lenient - just log warning
        if agent_name == "tester":
            logger.warning("%s expected output file missing: %s. Continuing anyway.", agent_name, file_path)
            return
        raise FileNotFoundError(f"{agent_name} expected output file missing: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    missing_sections = [
        section for section in validation["required_sections"] if f"{section}:" not in content
    ]
    if missing_sections:
        # For tester phase, be more lenient - just log warning
        if agent_name == "tester":
            logger.warning(
                "%s output missing some sections: %s. Continuing anyway.",
                agent_name,
                ", ".join(missing_sections),
            )
            return
        raise ValueError(
            f"{agent_name} output missing required sections: {', '.join(missing_sections)}"
        )
    logger.debug("Validated %s document at %s", agent_name, file_path)


def _extract_section_text(document: str, section_name: str) -> str:
    """Return the text for a named section in a structured document."""

    if not document:
        return ""

    # Sections are uppercase labels followed by colon
    pattern = rf"{section_name}:\s*(.*?)(?=\n[A-Z0-9_ ]+:\s*|\Z)"
    match = re.search(pattern, document, re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _tester_has_blockers(tester_output: str) -> tuple[bool, str]:
    """Determine if QA report indicates blockers that require rework."""

    if not tester_output.strip():
        return True, "Tester output missing; treating as failure."

    sign_off = _extract_section_text(tester_output, "SIGN_OFF")
    findings = _extract_section_text(tester_output, "FINDINGS")

    sign_off_upper = sign_off.upper() if sign_off else ""
    findings_upper = findings.upper() if findings else ""

    has_fail_sign_off = "FAIL" in sign_off_upper
    has_high_severity = "SEVERITY HIGH" in findings_upper or "HIGH -" in findings_upper

    if has_fail_sign_off or has_high_severity:
        reasons = []
        if has_fail_sign_off:
            reasons.append(f"SIGN_OFF indicates failure: {sign_off}")
        if has_high_severity:
            reasons.append("High severity findings present.")
        return True, " ".join(reasons).strip()

    if not sign_off:
        return True, "Tester output missing SIGN_OFF section."

    return False, ""


def _build_rework_payload(tester_output: str, attempt_index: int) -> str:
    """Create a payload for the engineer using QA tester feedback."""

    scope = _extract_section_text(tester_output, "SCOPE")
    findings = _extract_section_text(tester_output, "FINDINGS")
    patches = _extract_section_text(tester_output, "PATCHES")
    recommendations = _extract_section_text(tester_output, "RECOMMENDATIONS")

    payload = textwrap.dedent(
        f"""
        [QA_REWORK_REQUEST_ATTEMPT_{attempt_index}]
        QA_SCOPE:
        {scope or 'Scope unavailable.'}

        FINDINGS (fix only these issues):
        {findings or 'No findings text provided.'}

        PATCHES (follow exactly; do not change unrelated files):
        {patches or 'Tester did not provide explicit patch guidance; derive minimal edits from findings.'}

        ACTION ITEMS:
        {recommendations or 'Address each finding precisely, then rerun validations.'}

        IMPORTANT:
        - Only touch the files referenced above.
        - After applying fixes, ensure requirements from PROJECT PLAN remain satisfied.
        """
    ).strip()

    return f"{payload}\n\nFULL_QA_REPORT:\n{tester_output.strip()}"


@register_function(config_type=MASWorkflowConfig)
async def mas_workflow(config: MASWorkflowConfig, builder: Builder):
    """Register the MAS workflow coordinator as a NAT function.
    
    This coordinator chains the MAS phase functions sequentially and introduces a QA feedback loop:
    1. product_manager_phase - creates product specification from user request
    2. architect_phase - creates architecture design from PM output
    3. project_manager_phase - creates project plan from architect output
    4. engineer_phase - generates code files from project manager output
    5. tester_phase - validates generated deliverables and issues fix requests
    6. integrator_phase (optional) - summarizes final deliverables after QA sign-off
    
    Each phase function handles its own file I/O and brief prompts internally.
    """

    product_manager_phase_fn = builder.get_function(config.product_manager)
    architect_phase_fn = builder.get_function(config.architect)
    project_manager_phase_fn = builder.get_function(config.project_manager)
    engineer_phase_fn = builder.get_function(config.engineer)
    tester_phase_fn = builder.get_function(config.tester)
    integrator_phase_fn = None
    if config.integrator:
        try:
            integrator_phase_fn = builder.get_function(config.integrator)
        except Exception as exc:
            logger.warning("Could not initialize integrator function: %s", exc)
            integrator_phase_fn = None

    async def _response_fn(user_request: str) -> str:
        nonlocal integrator_phase_fn
        logger.info("Starting MAS workflow for request: %s", user_request)

        # Phase 1: Product Manager - uses user_request directly
        logger.info("Phase 1: Invoking product_manager_phase")
        phase1_start = time.time()
        pm_output: str = ""
        try:
            pm_output = await product_manager_phase_fn.ainvoke(user_request)
            phase1_elapsed = time.time() - phase1_start
            logger.info("Phase 1 (product_manager_phase) completed in %.2f seconds", phase1_elapsed)
        except ValueError as e:
            phase1_elapsed = time.time() - phase1_start
            if "STATUS line" in str(e):
                logger.warning(
                    "Product manager phase raised ValueError about STATUS line after %.2f seconds: %s. "
                    "Assuming file was saved and continuing.",
                    phase1_elapsed,
                    e,
                )
                pm_status = "Product specification saved (status extraction failed)"
            else:
                logger.error(
                    "Phase 1 (product_manager_phase) failed after %.2f seconds with unexpected ValueError: %s",
                    phase1_elapsed,
                    e,
                    exc_info=True,
                )
                raise
        else:
            try:
                pm_status = _extract_status("product_manager", pm_output)
                logger.info("Product manager phase completed with status: %s", pm_status)
            except ValueError as e:
                logger.warning("Could not extract product manager status: %s. Continuing to next phase anyway.", e)
                pm_status = "Product specification saved (status extraction failed)"
        _validate_document("product_manager")

        # Phase 2: Architect - reads pm_output.txt automatically
        logger.info("Phase 2: Invoking architect_phase")
        phase2_start = time.time()
        architect_output: str = ""
        try:
            architect_output = await architect_phase_fn.ainvoke("")  # user_request ignored, reads file instead
            phase2_elapsed = time.time() - phase2_start
            logger.info("Phase 2 (architect_phase) completed in %.2f seconds", phase2_elapsed)
        except ValueError as e:
            phase2_elapsed = time.time() - phase2_start
            if "STATUS line" in str(e):
                logger.warning(
                    "Architect phase raised ValueError about STATUS line after %.2f seconds: %s. "
                    "Assuming file was saved and continuing.",
                    phase2_elapsed,
                    e,
                )
                architect_status = "Architecture design saved (status extraction failed)"
            else:
                logger.error(
                    "Phase 2 (architect_phase) failed after %.2f seconds with unexpected ValueError: %s",
                    phase2_elapsed,
                    e,
                    exc_info=True,
                )
                raise
        else:
            try:
                architect_status = _extract_status("architect", architect_output)
                logger.info("Architect phase completed with status: %s", architect_status)
            except ValueError as e:
                logger.warning("Could not extract architect status: %s. Continuing to next phase anyway.", e)
                architect_status = "Architecture design saved (status extraction failed)"
        _validate_document("architect")

        # Phase 3: Project Manager - reads architect_output.txt automatically
        logger.info("Phase 3: Invoking project_manager_phase")
        phase3_start = time.time()
        project_manager_output: str = ""
        try:
            project_manager_output = await project_manager_phase_fn.ainvoke("")
            phase3_elapsed = time.time() - phase3_start
            logger.info("Phase 3 (project_manager_phase) completed in %.2f seconds", phase3_elapsed)
        except ValueError as e:
            phase3_elapsed = time.time() - phase3_start
            if "STATUS line" in str(e):
                logger.warning(
                    "Project manager phase raised ValueError about STATUS line after %.2f seconds: %s. "
                    "Assuming file was saved and continuing.",
                    phase3_elapsed,
                    e,
                )
                project_manager_status = "Project plan saved (status extraction failed)"
            else:
                logger.error(
                    "Phase 3 (project_manager_phase) failed after %.2f seconds: %s",
                    phase3_elapsed,
                    e,
                    exc_info=True,
                )
                raise
        else:
            try:
                project_manager_status = _extract_status("project_manager", project_manager_output)
                logger.info("Project manager phase completed with status: %s", project_manager_status)
            except ValueError as e:
                logger.warning("Could not extract project manager status: %s. Continuing to next phase anyway.", e)
                project_manager_status = "Project plan saved (status extraction failed)"
        _validate_document("project_manager")

        # Phase 4: Engineer - Generate code (single run, no retry loop)
        logger.info("Phase 4: Invoking engineer_phase")
        engineer_start = time.time()
        engineer_output = await engineer_phase_fn.ainvoke("")
        engineer_elapsed = time.time() - engineer_start
        logger.info("Phase 4 (engineer_phase) completed in %.2f seconds", engineer_elapsed)

        # Phase 5: Tester - Test and write report (single run, no feedback loop)
        tester_output = ""
        tester_document_text = ""
        qa_passed = False

        if tester_phase_fn is None:
            logger.warning("tester_phase function not configured; skipping QA phase.")
        else:
            logger.info("Phase 5: Invoking tester_phase")
            phase5_start = time.time()
            tester_output = await tester_phase_fn.ainvoke("")
            phase5_elapsed = time.time() - phase5_start
            logger.info("Phase 5 (tester_phase) completed in %.2f seconds", phase5_elapsed)

            try:
                tester_status = _extract_status("tester", tester_output)
                logger.info("Tester phase completed with status: %s", tester_status)
            except ValueError as e:
                logger.warning("Could not extract tester status: %s. Continuing.", e)
            _validate_document("tester")

            try:
                tester_document_text = Path("output/doc/tester_output.txt").read_text(encoding="utf-8")
            except FileNotFoundError:
                logger.warning("tester_output.txt not found when parsing QA report; falling back to agent output.")
                tester_document_text = tester_output

            # Check QA status for logging only (no retry loop)
            has_blockers, failure_reason = _tester_has_blockers(tester_document_text)
            if not has_blockers:
                qa_passed = True
                logger.info("QA tester sign-off: PASS")
            else:
                logger.warning("QA tester sign-off: FAIL - %s", failure_reason or "See tester report for details.")

        integrator_output = ""
        if builder and config.integrator:
            if integrator_phase_fn is None:
                try:
                    integrator_phase_fn = builder.get_function(config.integrator)
                except Exception as exc:
                    logger.error("Failed to initialize integrator function: %s", exc)
                    integrator_phase_fn = None

        if not tester_document_text and Path("output/doc/tester_output.txt").exists():
            try:
                tester_document_text = Path("output/doc/tester_output.txt").read_text(encoding="utf-8")
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Failed to read tester_output.txt for integrator context: %s", exc)
                tester_document_text = tester_output

        if integrator_phase_fn and (qa_passed or not config.require_pass_before_integrator):
            logger.info("Phase 6: Invoking integrator_phase (qa_passed=%s)", qa_passed)
            integrator_payload_lines = [
                "FINAL_STATUS_CONTEXT:",
                f"- QA_PASSED: {qa_passed}",
                f"- QA_SIGN_OFF: {_extract_section_text(tester_document_text, 'SIGN_OFF') or 'Unavailable'}",
                f"- QA_RECOMMENDATIONS: {_extract_section_text(tester_document_text, 'RECOMMENDATIONS') or 'Unavailable'}",
                "",
                "Refer to output/doc/tester_output.txt and project artifacts for details.",
            ]
            integrator_payload = "\n".join(integrator_payload_lines)

            try:
                integrator_output = await integrator_phase_fn.ainvoke(integrator_payload)
                logger.info("Integrator phase completed.")
                _validate_document("integrator")
            except ValueError as exc:
                logger.warning("Integrator phase raised ValueError: %s", exc)
            except Exception as exc:
                logger.error("Integrator phase failed: %s", exc, exc_info=True)

        if integrator_output:
            logger.info("MAS workflow completed; returning integrator output")
            return integrator_output
        if tester_output:
            logger.info("MAS workflow completed; returning tester output")
            return tester_output
        logger.info("MAS workflow completed; returning engineer output (no QA information available)")
        return engineer_output

    yield FunctionInfo.create(single_fn=_response_fn)
