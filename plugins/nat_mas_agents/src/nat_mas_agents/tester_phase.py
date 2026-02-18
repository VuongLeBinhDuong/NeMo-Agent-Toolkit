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

"""MAS workflow tester phase implementation."""

import logging
import re
import textwrap
from pathlib import Path
from typing import Awaitable, Callable

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig


TESTER_BRIEF = """
=== QA TESTER BRIEF ===
You are Phase 5 QA Tester. Your job is to READ and TEST code, NOT to modify it.

CRITICAL RULES:
- You MUST ONLY write to output/doc/tester_output.txt
- You MUST NEVER modify, overwrite, or save any files in the PROJECT_ARTIFACTS_DIR
- You MUST ONLY use file_reader to read files, NEVER use save_file_code on project files
- If you find issues, document them in the test report, DO NOT fix the code yourself

Your task:
1. Read the generated files using file_reader tool (read-only)
2. Check for basic issues (syntax errors, missing files, broken functionality)
3. Save ONLY a test report to output/doc/tester_output.txt

Workflow:
Thought: I will read the generated files and check for issues. I will NOT modify any files.
Action: file_reader
Action Input: {{"file_path": "output/PROJECT_NAME/filename.html"}}
Observation: [File content - READ ONLY]
[Repeat for other files as needed - HTML, CSS, JS, JSON files]
Thought: I've reviewed all files. Now I'll create the test report. I will ONLY write to output/doc/tester_output.txt.
Action: save_file_code
Action Input: {{"file_path": "output/doc/tester_output.txt", "code_content": "<QA REPORT TEXT>"}}
Observation: [Success message]
Thought: Test report saved successfully. I did NOT modify any project files.
Final Answer:
OUTPUT_FILE: output/doc/tester_output.txt
STATUS: Test report saved.

Key checks to perform (READ ONLY):
- Verify all required files exist (use file_reader to check)
- Check for syntax errors (read JSON, CSS, JS files and validate)
- Verify basic functionality (check if code structure is correct)
- Note any missing files or broken features

QA report format (include these sections):
PROJECT_NAME: [project name]
SCOPE: [what you tested - list of files you read]
VERIFICATIONS: [list what you checked - be specific about which files]
FINDINGS: [list any issues found, format: "Severity [CRITICAL|High|Medium|Low] - description - file: filename"]
PATCHES: [describe what needs to be fixed, but DO NOT write the fixes - just describe them]
RECOMMENDATIONS: [suggestions for improvements]
SIGN_OFF: [PASS if no critical issues, FAIL if critical issues found]

REMEMBER: You are a tester, not a developer. Document issues, don't fix them.
"""


logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "engineer": "Code generation completed",
    "tester": "Test report saved",
}


class MASWorkflowTesterPhaseConfig(FunctionBaseConfig, name="tester_phase"):
    """Configuration for the MAS workflow tester phase."""

    tester: FunctionRef


def _extract_status(agent_name: str, output_text: str) -> str:
    """Extract STATUS line from an agent's output. Returns default if not found."""

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
    # Return default status instead of raising error
    logger.warning("Could not extract STATUS from %s output, using default", agent_name)
    return DEFAULT_AGENT_STATUSES.get(agent_name, "Test report saved")


def _recover_status_from_tool_call(agent_name: str, output_text: str) -> str | None:
    """Attempt to recover STATUS by executing the agent's intended tool call.
    
    IMPORTANT: For tester phase, only recover if the file path is tester_output.txt
    to prevent accidentally overwriting project files.
    """

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

    file_path_str = file_path_match.group(1)
    file_path = Path(file_path_str)
    
    # For tester phase, only allow recovery for tester_output.txt
    # This prevents accidentally overwriting project files
    if agent_name == "tester":
        if "tester_output.txt" not in file_path_str:
            logger.warning(
                "Tester agent attempted to write to %s instead of tester_output.txt. "
                "Ignoring to prevent overwriting project files.",
                file_path_str
            )
            return None

    code_content = textwrap.dedent(code_match.group(1))
    normalized_content = (
        code_content.replace("\r\n", "\n")
        .replace("\u2022", "-")
        .replace("•", "-")
        .strip("\n")
    )

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

    result = await agent_call(payload)
    if not isinstance(result, str):
        raise TypeError(f"Expected {agent_name} output to be a string")
    return result


def _extract_content_from_file_reader_response(response: str) -> str:
    """Extract actual content from file_reader response."""
    content_marker = "Content:"
    content_idx = response.find(content_marker)

    if content_idx == -1:
        logger.warning("No 'Content:' marker found in file_reader response, returning as-is")
        return response

    extracted = response[content_idx + len(content_marker) :].lstrip("\n\r")
    logger.info("Successfully extracted content (length: %s chars)", len(extracted))
    return extracted


def _extract_project_name(content: str) -> str:
    """Extract PROJECT_NAME from project manager content and normalize to kebab-case."""
    from nat_mas_agents.config import normalize_project_name
    
    for line in content.splitlines():
        if line.strip().startswith("PROJECT_NAME:"):
            name = line.split(":", 1)[1].strip()
            if name:
                return normalize_project_name(name)
    return "project_output"


@register_function(config_type=MASWorkflowTesterPhaseConfig)
async def mas_tester_phase(config: MASWorkflowTesterPhaseConfig, builder: Builder):
    """Register the MAS workflow tester phase as a NAT function."""

    tester_fn = builder.get_function(config.tester)

    try:
        file_reader_fn = builder.get_function("file_reader")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("Could not get file_reader function: %s. QA agent must read files manually.", exc)
        file_reader_fn = None

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting QA tester phase for request: %s", user_request)

        # STEP 1: Read project manager output file for context
        pm_file_path = "output/doc/project_manager_output.txt"
        pm_content = None

        if file_reader_fn:
            try:
                logger.info("Reading project manager content from %s", pm_file_path)
                from nat.tool.file_reader import FileReaderInput

                file_reader_input = FileReaderInput(file_path=pm_file_path)
                file_reader_response = await file_reader_fn.ainvoke(file_reader_input)

                pm_content = _extract_content_from_file_reader_response(file_reader_response)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning("Error reading project manager file directly: %s. Agent must load file manually.", exc)
                pm_content = None
        else:
            logger.info("file_reader not available, tester agent must load project_manager_output.txt manually.")

        project_name = _extract_project_name(pm_content or "") if pm_content else "project_output"
        artifacts_dir = f"output/{project_name}"

        # Simplified message with clear restrictions
        tester_message = [
            TESTER_BRIEF.strip(),
            "",
            f"PROJECT_ARTIFACTS_DIR: {artifacts_dir}",
            "",
            "CRITICAL INSTRUCTIONS:",
            "- READ ONLY: Use file_reader to read files in the project directory above",
            "- DO NOT MODIFY: Never use save_file_code on any file in PROJECT_ARTIFACTS_DIR",
            "- WRITE ONLY: Save your test report ONLY to output/doc/tester_output.txt",
            "- Example file paths to read:",
            f"  - {artifacts_dir}/index.html",
            f"  - {artifacts_dir}/shop.html",
            f"  - {artifacts_dir}/styles.css",
            f"  - {artifacts_dir}/script.js",
            f"  - {artifacts_dir}/products.json",
            "",
            "REMEMBER: You are testing, not fixing. Document issues in the report only.",
        ]

        if pm_content:
            tester_message.extend(
                [
                    "",
                    "PROJECT_REQUIREMENTS:",
                    pm_content[:2000],  # Limit length to avoid overwhelming the agent
                ]
            )

        tester_payload = "\n".join(tester_message)

        try:
            tester_output = await _invoke_agent("tester", tester_fn.ainvoke, tester_payload)
            tester_status = _extract_status("tester", tester_output)
            logger.info("QA tester phase completed with status: %s", tester_status)
        except Exception as exc:
            logger.error("Tester phase failed: %s", exc, exc_info=True)
            # Create a minimal report if agent fails
            fallback_report = f"""PROJECT_NAME: {project_name}
SCOPE: Basic file existence check
VERIFICATIONS:
- Attempted to run QA tests
FINDINGS:
- High - QA tester phase encountered an error: {exc}
RECOMMENDATIONS:
- Review error logs and retry tester phase
SIGN_OFF: FAIL - Tester phase error occurred
"""
            try:
                Path("output/doc").mkdir(parents=True, exist_ok=True)
                Path("output/doc/tester_output.txt").write_text(fallback_report, encoding="utf-8")
                logger.info("Created fallback tester report")
            except Exception as write_exc:
                logger.error("Could not create fallback report: %s", write_exc)
            tester_output = f"Tester phase error: {exc}\n\n{fallback_report}"
            tester_status = "Test report saved (fallback)"

        return tester_output

    yield FunctionInfo.create(single_fn=_response_fn)

