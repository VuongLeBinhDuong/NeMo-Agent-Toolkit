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
You are Phase 5 QA Tester. You MUST follow strict ReAct format:

Thought: describe reasoning, which files you will inspect, and what validations you will run (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/tester_output.txt", "code_content": "<FULL QA REPORT>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/tester_output.txt
STATUS: Test report saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL QA REPORT> with the complete QA report body (no placeholders).
- Use file_reader to inspect any artifact referenced in the report; call it separately per file.
- If a file cannot be found/read, explicitly flag it as a High severity finding.
- Every finding that requires fixes MUST include a corresponding patch/diff summary in the PATCHES section (reference filenames, line ranges, and expected change; diff snippets encouraged).
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.

QA report body must include sections in order:
PROJECT_NAME:
SCOPE: (summarize what was tested, including directories and key requirements covered)
VERIFICATIONS: (bullet list describing each verification performed; reference requirement IDs or sections)
FINDINGS: (bullet list, format "Severity [High|Medium|Low] - description - Impact/Recommendation")
PATCHES: (bullet list; each entry must specify the file path, diff-style instructions, and minimal edits required to resolve associated findings. Provide ```diff``` snippets when possible.)
RECOMMENDATIONS: (bullet list of concrete follow-up actions)
SIGN_OFF: (one sentence concluding pass/fail status)
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
    """Extract PROJECT_NAME from project manager content."""
    for line in content.splitlines():
        if line.strip().startswith("PROJECT_NAME:"):
            name = line.split(":", 1)[1].strip()
            if name:
                return name
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

        project_name = _extract_project_name(pm_content or "")
        artifacts_dir = f"output/{project_name}"

        tester_message = [
            TESTER_BRIEF.strip(),
            "",
            f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['engineer']}",
            f"PROJECT_ARTIFACTS_DIR: {artifacts_dir}",
            "IMPORTANT:",
            "- Use file_reader to inspect any artifacts inside the directory above.",
            "- Verify requirements, categories, filters, shared header/footer, and cart behaviors.",
            "- If artifacts_dir does not exist, document it as a High severity finding.",
        ]

        if pm_content:
            tester_message.extend(
                [
                    "",
                    "EXTRACTED_PROJECT_MANAGER_CONTENT:",
                    pm_content,
                ]
            )
        else:
            tester_message.extend(
                [
                    "",
                    "Unable to inline project manager content. Load output/doc/project_manager_output.txt before testing.",
                ]
            )

        tester_payload = "\n".join(tester_message)

        tester_output = await _invoke_agent("tester", tester_fn.ainvoke, tester_payload)
        tester_status = _extract_status("tester", tester_output)

        logger.info("QA tester phase completed with status: %s", tester_status)
        return tester_output

    yield FunctionInfo.create(single_fn=_response_fn)

