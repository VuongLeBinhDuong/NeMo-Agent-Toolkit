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
from pathlib import Path
from typing import Awaitable, Callable

from pydantic import BaseModel, Field

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig


ARCHITECT_BRIEF = """
=== SYSTEM ARCHITECT BRIEF ===
You are Phase 2 System Architect. You MUST follow strict ReAct format:

Thought: describe reasoning (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/architect_output.txt", "code_content": "<FULL ARCHITECTURE DOCUMENT>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/architect_output.txt
STATUS: Architecture design saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL ARCHITECTURE DOCUMENT> with the complete architecture body (no placeholders).
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.
- Do NOT output the architecture document as plain text anywhere else and do not include PREVIOUS_STATUS.

Architecture body must include sections in order:
REQUIREMENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
PRODUCTS: (paste verbatim from EXTRACTED_PM_CONTENT)
CATEGORIES: (paste verbatim from EXTRACTED_PM_CONTENT)
SORT_OPTIONS: (paste verbatim from EXTRACTED_PM_CONTENT)
FUNCTIONALITY: (paste verbatim from EXTRACTED_PM_CONTENT)
UI_COMPONENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
FILE_REQUIREMENTS: (derive per-file responsibilities, use "- " bullets)
FILES: (comma-separated list, e.g. "index.html, styles.css, app.js")
ORDER: (arrow-separated, e.g. "index.html -> styles.css -> app.js")
"""


logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "product_manager": "Product specification saved",
    "architect": "Architecture design saved",
    "project_manager": "Project plan saved",
}


class MASWorkflowArchitectPhaseConfig(FunctionBaseConfig, name="architect_phase"):
    """Configuration for the MAS workflow architect phase."""

    architect: FunctionRef

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
    
    # Extract everything after "Content:" and the newline
    extracted = response[content_idx + len(content_marker):].lstrip('\n\r')
    logger.info(f'Successfully extracted content (length: {len(extracted)} chars)')
    return extracted


@register_function(config_type=MASWorkflowArchitectPhaseConfig)
async def mas_architect_phase(config: MASWorkflowArchitectPhaseConfig, builder: Builder):
    """Register the MAS workflow architect phase as a NAT function."""

    architect_fn = builder.get_function(config.architect)
    
    # Get file_reader tool
    try:
        file_reader_fn = builder.get_function("file_reader")
    except Exception as e:
        logger.warning(f"Could not get file_reader function: {e}. Will let agent handle file reading.")
        file_reader_fn = None

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting MAS workflow for request: %s", user_request)

        # STEP 1: Read PM spec file
        pm_file_path = "output/doc/pm_output.txt"
        pm_content = None
        
        if file_reader_fn:
            try:
                logger.info(f"Step 1: Reading PM spec from {pm_file_path}")
                from nat.tool.file_reader import FileReaderInput
                file_reader_input = FileReaderInput(file_path=pm_file_path)
                file_reader_response = await file_reader_fn.ainvoke(file_reader_input)
                
                # STEP 2: Extract content from file_reader response
                logger.info("Step 2: Extracting content from file_reader response")
                pm_content = _extract_content_from_file_reader_response(file_reader_response)
                logger.info(f"Extracted PM content (length: {len(pm_content)} chars)")
            except Exception as e:
                logger.warning(f"Error reading PM file directly: {e}. Will let agent handle it.")
                pm_content = None
        else:
            logger.info("file_reader not available, will let agent handle file reading")

        # STEP 3: Invoke architect with extracted content
        logger.info("Step 3: Invoking architect agent")
        
        if pm_content:
            # Include extracted content in the brief
            architect_message = (
                f"{ARCHITECT_BRIEF.strip()}\n\n"
                f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['product_manager']}\n\n"
                f"EXTRACTED_PM_CONTENT:\n{pm_content}\n\n"
                "IMPORTANT: Use the EXTRACTED_PM_CONTENT above to extract sections. "
            )
        else:
            # Fallback to original behavior
            architect_message = (
                f"{ARCHITECT_BRIEF.strip()}\n\nPREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['product_manager']}"
                "\nRemember to load output/doc/pm_output.txt before drafting the architecture."
            )
        
        architect_output = await _invoke_agent("architect", architect_fn.ainvoke, architect_message)
        architect_status = _extract_status("architect", architect_output)

        logger.info("MAS workflow completed; returning architect output")
        return architect_output

    yield FunctionInfo.create(single_fn=_response_fn)
