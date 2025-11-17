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

"""MAS workflow integrator phase implementation."""

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

INTEGRATOR_BRIEF = """
=== DELIVERY INTEGRATOR BRIEF ===
You are Phase 6 Delivery Integrator. You MUST follow strict ReAct format:

Thought: describe what artifacts you will inspect and how you will summarize the delivery (plain text)
Action: save_file_code
Action Input: {"file_path": "output/doc/integrator_output.txt", "code_content": "<FINAL DELIVERY REPORT>"}
Observation: Success message from tool
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/integrator_output.txt
STATUS: Integration summary saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FINAL DELIVERY REPORT> with the complete integration report (no placeholders).
- Read tester_output.txt, project_manager_output.txt, and any referenced artifacts via file_reader before citing them.
- When QA reported findings, explicitly reference the associated FIX_HISTORY entry and cite the file path plus expected diff.
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.

Final delivery report must include sections in order:
PROJECT_NAME: (short slug, copy from project manager output)
STATUS_SUMMARY: (2-3 sentences summarizing overall readiness and scope)
FIX_HISTORY: (bullet list referencing QA findings + patches applied; mention file paths and whether fixes are verified)
QA_STATUS: (single sentence referencing tester SIGN_OFF verdict and date/time if available)
DELIVERABLES: (bullet list enumerating shipped artifacts with relative paths, e.g., "output/<project>/index.html")
NEXT_STEPS: (bullet list outlining deployment, monitoring, or follow-up test actions)
SIGN_OFF: (final go/no-go statement with responsible role)
"""

logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "integrator": "Integration summary saved",
}


class MASWorkflowIntegratorPhaseConfig(FunctionBaseConfig, name="integrator_phase"):
    """Configuration for the MAS workflow integrator phase."""

    integrator: FunctionRef


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
    raise ValueError(f"{agent_name} did not return a STATUS line")


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


def _extract_content_from_file(path: str) -> str:
    """Read plaintext content from a file path if it exists."""

    file_path = Path(path)
    if not file_path.exists():
        logger.warning("Integrator could not locate %s", path)
        return ""
    return file_path.read_text(encoding="utf-8")


def _extract_project_name(content: str) -> str:
    """Extract PROJECT_NAME from project manager document."""

    for line in content.splitlines():
        if line.strip().startswith("PROJECT_NAME:"):
            project_name = line.split(":", 1)[1].strip()
            if project_name:
                return project_name
    return "project_output"


@register_function(config_type=MASWorkflowIntegratorPhaseConfig)
async def mas_integrator_phase(config: MASWorkflowIntegratorPhaseConfig, builder: Builder):
    """Register the MAS workflow integrator phase as a NAT function."""

    integrator_fn = builder.get_function(config.integrator)

    try:
        file_reader_fn = builder.get_function("file_reader")
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not get file_reader function: %s. Integrator agent must read files manually.", exc)
        file_reader_fn = None

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting integrator phase.")

        pm_content = _extract_content_from_file("output/doc/project_manager_output.txt")
        tester_content = _extract_content_from_file("output/doc/tester_output.txt")
        project_name = _extract_project_name(pm_content) if pm_content else "project_output"
        artifacts_dir = f"output/{project_name}"

        instructions = [
            INTEGRATOR_BRIEF.strip(),
            "",
            f"PROJECT_ARTIFACTS_DIR: {artifacts_dir}",
            f"QA_REPORT_PATH: output/doc/tester_output.txt",
            f"PROJECT_PLAN_PATH: output/doc/project_manager_output.txt",
            "",
        ]

        if pm_content:
            instructions.extend(
                [
                    "EXTRACTED_PROJECT_MANAGER_CONTENT:",
                    pm_content,
                    "",
                ]
            )
        else:
            instructions.append("Project manager content missing; load output/doc/project_manager_output.txt manually.")

        if tester_content:
            instructions.extend(
                [
                    "LATEST_QA_REPORT:",
                    tester_content,
                    "",
                ]
            )
        else:
            instructions.append("QA tester report missing; load output/doc/tester_output.txt manually.")

        if file_reader_fn:
            instructions.extend(
                [
                    "",
                    "NOTE: file_reader tool is available. Use it to inspect any artifact or report you cite.",
                ]
            )

        payload = "\n".join(instructions)
        integrator_output = await _invoke_agent("integrator", integrator_fn.ainvoke, payload)
        status = _extract_status("integrator", integrator_output)
        logger.info("Integrator phase completed with status: %s", status)
        return integrator_output

    yield FunctionInfo.create(single_fn=_response_fn)


