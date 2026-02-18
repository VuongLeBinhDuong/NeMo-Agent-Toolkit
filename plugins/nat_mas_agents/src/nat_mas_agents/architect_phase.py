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

from .sop_templates import get_component_snippets_text, get_sop_summary
from .structured_handoff import (
    format_handoff_for_agent,
    parse_pm_output_to_handoff,
    save_handoff_json,
)


def _get_architect_brief(website_type: str = "") -> str:
    """Get architect brief with SOP templates included.
    
    Args:
        website_type: Optional website type to customize SOPs. If not provided, returns generic version.
    """
    sop_summary = get_sop_summary(website_type)
    snippet_text = get_component_snippets_text(website_type)
    
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

{snippet_text}

CRITICAL: When specifying FILE_REQUIREMENTS, reference the SOP templates above for default behaviors.
DO NOT invent or guess component implementations - use the standardized specifications.

Architecture body must include sections in order:
REQUIREMENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
PRODUCTS: (paste verbatim from EXTRACTED_PM_CONTENT)
CATEGORIES: (paste verbatim from EXTRACTED_PM_CONTENT)
SORT_OPTIONS: (paste verbatim from EXTRACTED_PM_CONTENT)
FUNCTIONALITY: (paste verbatim from EXTRACTED_PM_CONTENT)
UI_COMPONENTS: (paste verbatim from EXTRACTED_PM_CONTENT)
SHARED_COMPONENTS: (paste verbatim from EXTRACTED_PM_CONTENT - must include header with search bar and, for ecommerce_site projects, cart section)
SHARED_ASSETS: (list shared files/resources such as global stylesheets, scripts, data sources.
  - For WEBSITE_TYPE = ecommerce_site:
    - CRITICAL: MUST include "products.json" – products/tickets will be loaded from JSON file, NEVER hardcoded in HTML.
    - Be specific: "styles.css", "script.js", "products.json".
    - Engineer MUST generate products.json file with ALL products from PRODUCTS section in correct format: array of objects with id, name, price, category, description, image.
  - For WEBSITE_TYPE = information_site or web_app:
    - Only include "products.json" if the PM REQUIREMENTS explicitly describe a structured catalog that must be loaded from JSON.
    - Otherwise, SHARED_ASSETS should focus on static assets such as "styles.css", "script.js" and any domain‑specific data sources (e.g., matches.json, results.json) explicitly requested.)
FILES: (comma-separated list of files that will be generated.
  - For WEBSITE_TYPE = ecommerce_site:
    - CRITICAL: Include "products.json" plus ALL required storefront HTML views: index.html, shop.html, cart.html, checkout.html, about.html (add additional ones if PM scope demands).
  - For WEBSITE_TYPE = information_site or web_app:
    - Derive pages from REQUIREMENTS (e.g., index.html, matches.html, results.html, about.html, dashboard.html, etc.) without introducing cart/checkout views unless explicitly required.
  - Include every HTML/CSS/JS/data artifact so downstream phases know they must be generated.
  - Example (ecommerce): "index.html, shop.html, cart.html, checkout.html, about.html, styles.css, script.js, products.json"
  - Example (information_site): "index.html, matches.html, results.html, about.html, styles.css, script.js")
ORDER: (arrow-separated order in which files should be produced.
  - For ecommerce_site: products.json is typically generated early (before or alongside HTML files) so JavaScript can load it.
  - Recommended order for ecommerce_site: products.json -> HTML files -> CSS -> JS
  - For information_site / web_app: choose an order that keeps HTML before CSS/JS, but do not introduce products.json unless it is part of FILES.
  - Example (ecommerce): "products.json -> index.html -> shop.html -> cart.html -> checkout.html -> about.html -> styles.css -> script.js"
  - Example (information_site): "index.html -> matches.html -> results.html -> about.html -> styles.css -> script.js")
FILE_REQUIREMENTS: (derive per-file responsibilities; one bullet per file. Reference SOP templates and code examples for details.)
  - HTML:
    - Reference HEADER/FOOTER SOPs for structure.
    - For ecommerce_site product listing pages: MUST have empty container id="products-container" (products loaded from JSON, NEVER hardcoded) and include filter/sort controls. Use relative paths for links.
    - For information_site pages: define appropriate containers for domain entities (e.g., matches, results) and only use id="products-container"/products.json if explicitly required in PM/architect requirements.
  - products.json (only when FILES includes products.json):
    - For ecommerce_site projects: CRITICAL – MUST be generated with ALL products from PRODUCTS section. Format: array of objects with id, name, price, category, description, image properties. Save to output/[PROJECT_NAME]/products.json.
    - For other WEBSITE_TYPE values: only define products.json if the domain explicitly calls for a product/catalog JSON source.
  - script.js:
    - For ecommerce_site: Reference CART, FILTER, SORT, SEARCH SOPs. Use id="products-container". Check elements exist before using. MUST load products from products.json using fetch(). Use ES6+ classes for organization. Implement Intersection Observer for lazy loading, modal management, state management, and performance optimizations. Cart page: render to #cart-items.
    - For information_site / web_app: focus on rendering, filtering, sorting, and searching domain entities (e.g., matches, results) and only implement cart/checkout/product loading behaviors if explicitly required.
  - styles.css: Reference code examples for full design system. Define CSS variables/design tokens, global resets, layout containers, sticky header/nav, hero banner, filter/sort/search toolbar, product grid/cards, cart + checkout forms, modals/toasts, utility classes, dark mode + prefers-reduced-motion support, and loading states.
  - NAMING CONTRACT (CRITICAL): All shared layout components MUST use the following BEM-style class names consistently across EVERY HTML file and in styles.css. Do NOT invent alternative names such as "site-header" or "primary-nav" in CSS if the HTML uses the canonical names below:
      * Header (shared on all pages): header, header__container, header__logo, header__nav, header__nav-list, header__nav-item, header__nav-link, header__search, header__search-input (id="search-input"), header__cart, header__cart-link, header__cart-icon, header__cart-count (id="cart-count"), header__cart-subtotal (id="cart-subtotal").
      * Footer (shared on all pages): footer, footer__container, footer__about, footer__about-title, footer__about-text, footer__nav, footer__nav-list, footer__nav-item, footer__nav-link, footer__social, footer__social-list, footer__social-item, footer__social-link, footer__social-icon, footer__bottom, footer__bottom-text.
      * Product listing: products, products__title, products__container (id="products-container"), product-card, product-card__image, product-card__info, product-card__title, product-card__price, product-card__category, product-card__description, product-card__badge, product-card__actions, product-card__button (e.g., .add-to-cart-btn).
      * Shop controls: shop-controls, shop-controls__filter, shop-controls__sort, shop-controls__label, shop-controls__select (with ids filter-select/category-filter and sort-select/sort-by as defined in SOPs).
    HTML and CSS MUST both use these exact class names for the shared components above. If you reference a shared component in FILE_REQUIREMENTS, you MUST also ensure that at least one HTML file and styles.css both declare matching selectors for that component.
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
                f"{architect_brief.strip()}\n\nPREVIOUS_STATUS: {DEFAULT_AGENT_STATUSES['product_manager']}"
                "\nRemember to load output/doc/pm_output.txt before drafting the architecture."
            )
        
        architect_output = await _invoke_agent("architect", architect_fn.ainvoke, architect_message)
        architect_status = _extract_status("architect", architect_output)

        logger.info("MAS workflow completed; returning architect output")
        return architect_output

    yield FunctionInfo.create(single_fn=_response_fn)
