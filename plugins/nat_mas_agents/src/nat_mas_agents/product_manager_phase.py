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

from .config import get_config
from .sop_templates import get_component_snippets_text, get_sop_summary


def _get_product_manager_brief() -> str:
    """Get product manager brief with SOP templates included."""
    sop_summary = get_sop_summary()
    snippet_text = get_component_snippets_text()
    
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
PROJECT_NAME: (project name in kebab-case format, e.g., "tech-gadget-store" or "fashion-marketplace")
WEBSITE_TYPE: (one of: information_site, ecommerce_site, web_app)
REQUIREMENTS: (3-5 sentences covering context, goals, users, success criteria)
FEATURES: (bullet list)
PRODUCTS: (For ecommerce_site projects: CRITICAL – List at least 6-10 real products/ticketed items with specific names, exact prices, categories, and detailed descriptions. Format: "Product Name: $XX.XX, Category Name, Full description text". For information_site projects, you may instead list key entities to be displayed (e.g., leagues, matches, competitions) without implying they are for sale.)
CATEGORIES: (list all unique categories from PRODUCTS/entities above)
SORT_OPTIONS: (list sorting options like "Price: Low to High", "Price: High to Low", "Name: A to Z", or domain‑specific options like "Date: Newest First" / "League: A–Z" for information sites.)
FUNCTIONALITY: (bullet list of behavioural requirements; for ecommerce_site include: products loaded from products.json via JavaScript fetch(), localStorage for cart, filtering, sorting, search, checkout; for information_site focus on browsing, filtering, searching content without cart/checkout unless explicitly requested.)
UI_COMPONENTS: (bullet list with identifiers/classes including: header with logo/menu/search (and cart only for ecommerce_site), footer, main content sections such as product grid or match listings, etc.)
PAGE_REQUIREMENTS: (bullet list of per-page requirements with specific details)
SUCCESS_CRITERIA: (bullet list of measurable outcomes/KPIs)
SHARED_COMPONENTS: (bullet list including: responsive header with logo, menu, search bar; for ecommerce_site also include cart section showing item count and subtotal, footer)

{sop_summary}

{snippet_text}

CRITICAL: When specifying SHARED_COMPONENTS, reference the SOP templates above for default behaviors.
The system has standardized implementations for header, footer, cart, filter, sort, and search components.

Additional rules:
- WEBSITE_TYPE classification:
  - Use "ecommerce_site" ONLY when the user explicitly mentions selling/buying, pricing, cart, checkout, payment, orders, or ticket purchases.
  - Use "web_app" when the focus is on dashboards, tools, CRUD flows, or authenticated apps rather than pure content or classic storefront shopping.
  - In all other cases (pure content, schedules, results, articles, documentation, blogs), default to "information_site".
- Never use placeholder text (TBD, lorem ipsum, "Product 1", "Product 2", etc.). Use real names and domain‑appropriate details.
- Ensure PRODUCTS/Entities, CATEGORIES, SORT_OPTIONS align perfectly.
- For ecommerce_site:
  - CRITICAL: Products MUST be loaded from products.json file via JavaScript fetch(). Products must NEVER be hardcoded in HTML files. This is a hard requirement.
  - SHARED_COMPONENTS must explicitly mention: header with search bar (#search-input) and cart section (#cart-count, #cart-subtotal) as per HEADER SOP.
  - SHARED_ASSETS must include "products.json" – this file will contain all products from PRODUCTS section.
- For information_site or web_app:
  - DO NOT introduce cart, checkout, or products.json unless the requirements explicitly request commerce flows.
  - SHARED_COMPONENTS may omit cart/checkout entirely if the project is purely informational.
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


def _ensure_product_section(file_path: Path) -> None:
    """Ensure pm_output.txt begins with PRODUCT header for validation."""

    if not file_path.exists():
        logger.warning("Cannot enforce PRODUCT header; %s does not exist", file_path)
        return

    content = file_path.read_text(encoding="utf-8")
    if content.lstrip().startswith("PRODUCT:"):
        return

    product_name = ""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped:
            product_name = stripped
            break

    if not product_name:
        product_name = "Product Specification"

    new_content = f"PRODUCT:\n{product_name}\n\n{content}"
    file_path.write_text(new_content, encoding="utf-8")
    logger.info("Inserted missing PRODUCT header into %s", file_path)


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

        pm_file = Path("output/doc/pm_output.txt")
        _ensure_product_section(pm_file)
        
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
