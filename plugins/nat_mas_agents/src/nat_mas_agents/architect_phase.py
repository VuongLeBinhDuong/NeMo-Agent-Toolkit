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

from .sop_templates import get_sop_summary
from .structured_handoff import (
    format_handoff_for_agent,
    parse_pm_output_to_handoff,
    save_handoff_json,
)


def _get_architect_brief() -> str:
    """Get architect brief with SOP templates included."""
    sop_summary = get_sop_summary()
    
    return f"""
=== SYSTEM ARCHITECT BRIEF ===
You are Phase 2 System Architect. You MUST follow strict ReAct format:

Thought: describe reasoning and the files to be created (plain text, no JSON)
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
- The files to be created are reasoned by the architect in the Thought section.
- After the Observation from save_file_code, immediately provide the Final Answer block exactly as shown.
- Do NOT output the architecture document as plain text anywhere else and do not include PREVIOUS_STATUS.

{sop_summary}

CRITICAL: When specifying FILE_REQUIREMENTS, reference the SOP templates above for default behaviors.
DO NOT invent or guess component implementations - use the standardized specifications.

Architecture body must include sections in order:
REQUIREMENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
PRODUCTS: (paste verbatim from EXTRACTED_PM_CONTENT)
CATEGORIES: (paste verbatim from EXTRACTED_PM_CONTENT)
SORT_OPTIONS: (paste verbatim from EXTRACTED_PM_CONTENT)
FUNCTIONALITY: (paste verbatim from EXTRACTED_PM_CONTENT)
UI_COMPONENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
SHARED_COMPONENTS: (paste verbatim from EXTRACTED_PM_CONTENT - must include header with search bar and cart section)
SHARED_ASSETS: (list shared files/resources such as global stylesheets, scripts, data sources. 
  - CRITICAL: Include "products.json" if products should be loaded from JSON file instead of hardcoded in HTML. This is recommended for multi-page projects.
  - Be specific: "styles.css", "script.js", "products.json", etc.
  - If products.json is included, engineer MUST generate this file with ALL products from PRODUCTS section in correct format: array of objects with id, name, price, category, description, image)
FILES: (comma-separated list of files that will be generated. 
  - CRITICAL: If "products.json" is in SHARED_ASSETS, you MUST include "products.json" in FILES list.
  - Include all HTML files, CSS files, JS files, and products.json (if in SHARED_ASSETS).
  - Example: "index.html, shop.html, cart.html, styles.css, script.js, products.json")
ORDER: (arrow-separated order in which files should be produced.
  - CRITICAL: If "products.json" is in SHARED_ASSETS, it should be generated EARLY (before or alongside HTML files) so JavaScript can load it.
  - Recommended order: products.json (if in SHARED_ASSETS) -> HTML files -> CSS -> JS, or products.json -> HTML -> CSS -> JS
  - Example: "products.json -> index.html -> shop.html -> cart.html -> styles.css -> script.js" OR "index.html -> shop.html -> cart.html -> styles.css -> script.js -> products.json")
FILE_REQUIREMENTS: (derive per-file responsibilities with DETAILED requirements; one bullet per file. 
  - For HTML files: 
    * CRITICAL: EVERY HTML page MUST have IDENTICAL header structure with: logo (clickable, links to homepage), navigation menu (links to ALL pages), search input (#search-input on input element itself), cart section (#cart-count, #cart-subtotal). Header must be professional, modern, and responsive.
    * CRITICAL: EVERY HTML page MUST have IDENTICAL footer structure with: company info, navigation links, contact info, copyright. Footer must be professional, modern, dark background, light text, responsive (3 columns desktop, stacked mobile).
    * Products can be EITHER hardcoded directly in HTML OR loaded from products.json file. 
    * If products.json is in SHARED_ASSETS: HTML MUST have empty product container with id="products-container" (with 's', plural). Example: <section id="products-container" class="product-container"></section>. DO NOT hardcode products in HTML - leave container empty. JavaScript will load products from JSON.
    * For product listing pages (shop.html, index.html): MUST include filter and sort controls above or near the product container:
      - Category filter dropdown: <select id="filter-select"> or <select id="category-filter"> with options for all categories
      - Sort dropdown: <select id="sort-select"> or <select id="sort-by"> with sort options
    * If products.json is NOT in SHARED_ASSETS: Products MUST be hardcoded directly in HTML markup with data attributes (data-category, data-price) for filtering/sorting.
  - For products.json (if in SHARED_ASSETS):
    * Engineer MUST generate this file with ALL products from PRODUCTS section
    * Format: Array of objects, each with id (number), name (string), price (number), category (string), description (string), image (string URL)
    * Example: [{{"id": 1, "name": "Product Name", "price": 29.99, "category": "Category", "description": "Description", "image": "https://via.placeholder.com/300x300?text=Product"}}]
    * Save to: output/[PROJECT_NAME]/products.json
    * CRITICAL: This file MUST be generated so JavaScript can load it
  - For script.js: 
    * CRITICAL: Use id="products-container" (with 's', plural) consistently. Use document.getElementById('products-container') to get the product container.
    * If products.json exists in SHARED_ASSETS: MUST load products from products.json using fetch('products.json') on DOMContentLoaded
      - Parse JSON response: Handle both formats - if response is a direct array (starts with square bracket), use it directly; if response is an object with a "products" property, extract the products array from that property; otherwise use empty array
      - Generate product cards dynamically and insert into #products-container
      - Handle fetch errors with fallback (hardcoded products or error message)
    * If products.json NOT in SHARED_ASSETS: Use hardcoded products array or read from HTML
    * For multi-page projects: JavaScript must detect current page and initialize appropriate functionality (product listing, cart display, etc.)
    * Reference CART, FILTER, SORT, SEARCH SOPs - must implement all standard behaviors exactly as specified
    * CRITICAL: All event listeners MUST check if elements exist before attaching: First get the element using getElementById or querySelector, check if it exists (not null), and only then attach the event listener
    * Event listeners for: #search-input (search), #filter-select or #category-filter (filter), #sort-select or #sort-by (sort)
    * updateCartDisplay() must be called after every cart operation AND on page load
    * Cart must update header cart display (#cart-count, #cart-subtotal) on ALL pages
  - For header component: reference HEADER SOP - must include logo (left, clickable), menu/nav links to ALL pages (center), search bar input (#search-input on the input element itself), cart section (#cart-count, #cart-subtotal) on right. Header structure must be IDENTICAL across all HTML pages. Modern, professional design with proper spacing.
  - For footer component: reference FOOTER SOP - must include company info, navigation links, contact info, copyright. Footer structure must be IDENTICAL across all HTML pages. Dark background, light text, responsive multi-column layout.
  - For styles.css: 
    * Modern, beautiful, professional styling - NOT basic or ugly
    * Responsive product grid (3-4 columns desktop, 2 columns tablet, 1 column mobile)
    * Product cards: Modern card design with subtle shadows, rounded corners, smooth hover effects
    * Header: Clean, professional design with proper spacing, modern layout (flexbox or grid), responsive
    * Footer: Clean, modern design with dark background, light text, responsive multi-column layout
    * Reference component styles from SOPs. Styles must work consistently across all pages.
  - Be explicit about which files/modules implement which components and how they integrate across multiple pages.)
"""

ARCHITECT_BRIEF = _get_architect_brief()


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

        # STEP 3: Parse PM content into structured handoff
        pm_handoff = None
        structured_handoff_text = ""
        
        if pm_content:
            try:
                pm_handoff = parse_pm_output_to_handoff(pm_content)
                structured_handoff_text = format_handoff_for_agent(pm_handoff)
                logger.info("Created structured handoff from PM output")
                
                # Save structured handoff JSON for downstream phases
                save_handoff_json(pm_handoff, "output/doc/pm_handoff.json")
            except Exception as e:
                logger.warning(f"Error creating structured handoff: {e}. Using text-based handoff.")
                structured_handoff_text = f"EXTRACTED_PM_CONTENT:\n{pm_content}\n\n"
        
        # STEP 4: Invoke architect with structured handoff and SOP templates
        logger.info("Step 4: Invoking architect agent")
        
        if pm_content:
            # Include structured handoff in the brief
            architect_message = (
                f"{ARCHITECT_BRIEF.strip()}\n\n"
                f"PREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['product_manager']}\n\n"
                f"{structured_handoff_text}\n\n"
                "IMPORTANT: Use the structured handoff data above to extract sections. "
                "Reference SOP templates for default component behaviors. "
                "Be explicit about which files/modules implement which shared components and assets."
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
