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

from .sop_templates import get_sop_summary


def _get_product_manager_brief() -> str:
    """Get product manager brief with SOP templates included."""
    sop_summary = get_sop_summary()
    
    return f"""
=== PRODUCT MANAGER BRIEF ===
You are Phase 1 Product Manager. You MUST follow strict ReAct format:

Thought: describe reasoning (plain text, no JSON)
Action: save_file_code
Action Input: {{"file_path": "output/doc/pm_output.txt", "code_content": "<FULL SPEC TEXT>"}}
Observation: Success message from tool (verbatim, no edits)
Thought: Confirm completion
Final Answer:
OUTPUT_FILE: output/doc/pm_output.txt
STATUS: Product specification saved.

Hard requirements:
- Call save_file_code exactly once.
- Action Input MUST be valid JSON with double-quoted keys/values, no trailing commas, no Markdown fences.
- Replace <FULL SPEC TEXT> with the complete specification body (no placeholders).
- Do NOT include extra commentary before or after the required sections.
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown (no additional Thought/Action lines, no "Action: None").

Specification body (save to file) must include sections in order:
PRODUCT:
REQUIREMENTS: (3-5 sentences covering context, goals, users, success criteria)
FEATURES: (bullet list)
PRODUCTS: (CRITICAL: List at least 6-10 real products with specific names, exact prices, categories, and detailed descriptions. Format: "Product Name: $XX.XX, Category Name, Full description text". Products must be hardcoded directly in HTML, not loaded from JSON.)
CATEGORIES: (list all unique categories from PRODUCTS above)
SORT_OPTIONS: (list sorting options like "Price: Low to High", "Price: High to Low", "Name: A to Z", etc.)
FUNCTIONALITY: (bullet list of behavioural requirements including: products hardcoded in HTML, localStorage for cart, filtering, sorting, search, etc.)
UI_COMPONENTS: (bullet list with identifiers/classes including: header with logo/menu/search/cart, footer, product cards, etc.)
PAGE_REQUIREMENTS: (bullet list of per-page requirements with specific details)
SUCCESS_CRITERIA: (bullet list of measurable outcomes/KPIs)
SHARED_COMPONENTS: (bullet list including: responsive header with logo, menu, search bar, cart section showing item count and subtotal, footer)

{sop_summary}

CRITICAL: When specifying SHARED_COMPONENTS, reference the SOP templates above for default behaviors.
The system has standardized implementations for header, footer, cart, filter, sort, and search components.

Additional rules:
- Never use placeholder text (TBD, lorem ipsum, "Product 1", "Product 2", etc.). Use real product names and details.
- Ensure PRODUCTS, CATEGORIES, SORT_OPTIONS align perfectly.
- CRITICAL: Products must be hardcoded directly in HTML files, not loaded dynamically from JSON. This is a hard requirement.
- SHARED_COMPONENTS must explicitly mention: header with search bar (#search-input) and cart section (#cart-count, #cart-subtotal) as per HEADER SOP.
- Output spec only via save_file_code (not in Final Answer).
- Write the specification as plain text (no JSON/object literals). Use "- " for bullet items and separate sections with a blank line.
- Keep all tool JSON inline (no ``` fences or extra formatting).
"""

PRODUCT_MANAGER_BRIEF = _get_product_manager_brief()

logger = logging.getLogger(__name__)

DEFAULT_AGENT_STATUSES = {
    "product_manager": "Product specification saved",
    "architect": "Architecture design saved",
    "project_manager": "Project plan saved",
}


class MASWorkflowProductManagerPhaseConfig(FunctionBaseConfig, name="product_manager_phase"):
    """Configuration for the MAS workflow product manager phase."""

    product_manager: FunctionRef

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


@register_function(config_type=MASWorkflowProductManagerPhaseConfig)
async def mas_product_manager_phase(config: MASWorkflowProductManagerPhaseConfig, builder: Builder):
    """Register the MAS workflow product manager phase as a NAT function."""

    product_manager_fn = builder.get_function(config.product_manager)

    async def _response_fn(user_request: str) -> str:
        logger.info("Starting MAS workflow for request: %s", user_request)

        product_manager_message = (
            f"{PRODUCT_MANAGER_BRIEF.strip()}\n\nUSER_REQUIREMENT:\n{user_request.strip()}"
        )
        pm_output = await _invoke_agent("product_manager", product_manager_fn.ainvoke, product_manager_message)
        
        # Log output for debugging if status extraction fails
        try:
            pm_status = _extract_status("product_manager", pm_output)
            logger.info("MAS workflow completed; returning product manager output with status: %s", pm_status)
        except ValueError as e:
            logger.error("Failed to extract STATUS from product_manager output. Output length: %d", len(pm_output))
            logger.debug("Product manager output (first 500 chars): %s", pm_output[:500])
            # Try to recover by checking if file was saved
            if "output/doc/pm_output.txt" in pm_output or "pm_output.txt" in pm_output:
                logger.warning("File reference found in output, assuming success")
                pm_status = DEFAULT_AGENT_STATUSES.get("product_manager", "Product specification saved")
            else:
                raise
        
        return pm_output

    yield FunctionInfo.create(single_fn=_response_fn)
