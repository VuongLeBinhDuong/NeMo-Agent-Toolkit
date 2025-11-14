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

from nat.builder.builder import Builder
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.component_ref import FunctionRef
from nat.data_models.function import FunctionBaseConfig

PROJECT_MANAGER_BRIEF = """
=== PROJECT MANAGER BRIEF ===
You are Phase 3 Project Manager. You MUST follow strict ReAct format:

Thought: describe reasoning (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/project_manager_output.txt", "code_content": "<FULL PROJECT PLAN>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/project_manager_output.txt
STATUS: Project plan saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL PROJECT PLAN> with the complete project plan body (no placeholders).
- The constraints are reasoned by the project manager in the Thought section.
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.
- Do NOT output the project plan as plain text anywhere else.

Project plan body must include sections in order:
PROJECT_NAME: (short slug derived from requirements, lowercase, hyphen separated)
REQUIREMENTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
SHARED_COMPONENTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
SHARED_ASSETS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
FILES: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
ORDER: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
FILE_REQUIREMENTS: (paste verbatim from EXTRACTED_ARCHITECT_CONTENT)
STEPS: (one entry per file in numeric order. CRITICAL: Each step must be on a separate line. Format: "Step N: [filename]" followed by " Constraints: [constraints text]" on the same line. The constraints should contain (1) one-sentence restatement of overall REQUIREMENTS context, (2) the exact FILE_REQUIREMENTS bullet with ALL details, (3) explicit references to relevant PRODUCTS (list actual product names/prices from PRODUCTS section), CATEGORIES, SORT_OPTIONS, FUNCTIONALITY, UI_COMPONENTS, and (4) for HTML files: specify that products must be hardcoded directly in the HTML (not loaded from JSON), list the actual products to include, for header: specify it must include search bar input and cart section with item count and subtotal, for script.js: specify it must implement filtering, sorting, search, localStorage cart operations, add to cart, quantity controls, totals. Use plain sentences, no JSON)
Example format:
STEPS:
Step 1: filename1 Constraints: [full constraints text here]
Step 2: filename2 Constraints: [full constraints text here]
Step 3: filename3 Constraints: [full constraints text here]
...
"""

logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "product_manager": "Product specification saved",
    "architect": "Architecture design saved",
    "project_manager": "Project plan saved",
}


class MASWorkflowProjectManagerPhaseConfig(FunctionBaseConfig, name="project_manager_phase"):
    """Configuration for the MAS workflow project manager phase."""

    project_manager: FunctionRef


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


@register_function(config_type=MASWorkflowProjectManagerPhaseConfig)
async def mas_project_manager_phase(config: MASWorkflowProjectManagerPhaseConfig, builder: Builder):
    """Register the MAS workflow project manager phase as a NAT function."""

    project_manager_fn = builder.get_function(config.project_manager)
    
    # Get file_reader tool
    try:
        file_reader_fn = builder.get_function("file_reader")
    except Exception as e:
        logger.warning(f"Could not get file_reader function: {e}. Will let agent handle file reading.")
        file_reader_fn = None

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting MAS workflow for request: %s", user_request)

        # STEP 1: Read architect output file
        architect_file_path = "output/doc/architect_output.txt"
        architect_content = None
        
        if file_reader_fn:
            try:
                logger.info(f"Step 1: Reading architect output from {architect_file_path}")
                from nat.tool.file_reader import FileReaderInput
                file_reader_input = FileReaderInput(file_path=architect_file_path)
                file_reader_response = await file_reader_fn.ainvoke(file_reader_input)
                
                # STEP 2: Extract content from file_reader response
                logger.info("Step 2: Extracting content from file_reader response")
                architect_content = _extract_content_from_file_reader_response(file_reader_response)
                logger.info(f"Extracted architect content (length: {len(architect_content)} chars)")
            except Exception as e:
                logger.warning(f"Error reading architect file directly: {e}. Will let agent handle it.")
                architect_content = None
        else:
            logger.info("file_reader not available, will let agent handle file reading")

        # STEP 3: Invoke project manager with extracted content
        logger.info("Step 3: Invoking project manager agent")
        
        if architect_content:
            # Include extracted content in the brief
            project_manager_message = (
                f"{PROJECT_MANAGER_BRIEF.strip()}\n\n"
                f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['architect']}\n\n"
                f"EXTRACTED_ARCHITECT_CONTENT:\n{architect_content}\n\n"
                "IMPORTANT: Use the EXTRACTED_ARCHITECT_CONTENT above to extract sections. "
            )
        else:
            # Fallback to original behavior
            project_manager_message = (
                f"{PROJECT_MANAGER_BRIEF.strip()}\n\nPREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['architect']}"
                "\nRemember to read output/doc/architect_output.txt before planning."
            )
        
        project_manager_output = await _invoke_agent(
            "project_manager", project_manager_fn.ainvoke, project_manager_message
        )
        project_manager_status = _extract_status("project_manager", project_manager_output)

        logger.info("MAS workflow completed; returning project manager output")
        return project_manager_output

    yield FunctionInfo.create(single_fn=_response_fn)
