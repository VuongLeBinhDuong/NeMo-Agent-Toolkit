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

"""Reusable sections that compose the MAS engineer prompt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PromptSection:
    """Declarative container for prompt sections."""

    title: str
    bullets: tuple[str, ...]

    def render(self) -> str:
        bullet_lines = "\n".join(f"- {bullet}" for bullet in self.bullets)
        return f"{self.title}\n{bullet_lines}"


PROMPT_SECTIONS: dict[str, PromptSection] = {
    "project_alignment": PromptSection(
        "=== PROJECT ALIGNMENT ===",
        (
            "Use PROJECT_NAME, FILES, ORDER, and STEPS exactly as defined in the structured handoff data.",
            "Treat STEP[n].constraints as the single source of truth for each file—feed them directly to code_generation_tool.",
            "Extract PROJECT_NAME from the handoff and reuse that exact, case-sensitive value for every output path.",
            "Never rename or alter filenames; honor the provided casing across code generation and save_file_code inputs.",
            "Respect REQUIREMENTS, SHARED_COMPONENTS, SHARED_ASSETS, and FILE_REQUIREMENTS for every deliverable.",
        ),
    ),
    "react_sequence": PromptSection(
        "=== STEP EXECUTION SEQUENCE ===",
        (
            "Process STEPS sequentially: Thought (plan file) → Action: code_generation_tool → Observation → Thought → Action: save_file_code.",
            "After every Observation from code_generation_tool you MUST produce another Thought before the next Action.",
            "Do not introduce extra files; only generate those listed in ORDER.",
        ),
    ),
    "html_structure": PromptSection(
        "=== HTML STRUCTURE RULES ===",
        (
            "Every HTML page must share identical header and footer structures built with flexbox or grid for responsive layouts.",
            "Headers need a clickable logo linking to index.html, navigation links to all pages, #search-input on the input element, and a cart summary using #cart-count and #cart-subtotal.",
            "Footers must show company info, navigation links, contact info, and copyright with a dark (#343a40) background.",
            "Do not use inline styles or <style> tags; keep HTML presentation-free and link shared CSS/JS assets exactly as named.",
            "Product listing pages require visible filter and sort controls (e.g., #filter-select/#category-filter and #sort-select/#sort-by) above the product container.",
            "Reference shared CSS via <link rel=\"stylesheet\" href=\"styles.css\"> (or the specified filename) and place <script src=\"script.js\"></script> immediately before </body>—never after </html>.",
            "Avoid fixed-position footers unless additional bottom padding prevents overlap.",
        ),
    ),
    "product_data": PromptSection(
        "=== PRODUCT & ASSET HANDLING ===",
        (
            'If SHARED_ASSETS includes products.json, leave an empty container with id="products-container" in HTML and never hardcode product markup.',
            'Use the same "products-container" id inside JavaScript when rendering dynamic product cards.',
            "When products.json is absent, hardcode product cards in HTML but still wrap them in the shared container and include data attributes.",
            "products.json must contain every product (id, name, price, category, description, image) and live at output/[PROJECT_NAME]/products.json before HTML/JS depend on it.",
            "Maintain exact SHARED_ASSETS filenames (styles.css, script.js, products.json, etc.) when linking or fetching resources.",
        ),
    ),
    "javascript_behavior": PromptSection(
        "=== JAVASCRIPT BEHAVIOR ===",
        (
            "When products.json exists, load it via fetch('products.json') on DOMContentLoaded and handle both raw arrays and objects containing a products property.",
            "Gracefully handle fetch failures by falling back to hardcoded data or surfacing a helpful error so the UI is never empty.",
            "If products.json is missing, define a hardcoded products array but keep filtering, sorting, and rendering logic identical.",
            "Render product cards dynamically with data-category and data-price attributes to support filtering and sorting.",
            "Cart logic must use localStorage key \"cart\", call updateCartDisplay() after every change and on load, and update header counters on every page.",
            "Attach event listeners only after confirming the target elements exist (filters, sorts, search input, add-to-cart buttons, cart controls).",
            "Detect the active page (window.location.pathname or sentinel elements) and initialize only the relevant behaviors for that view.",
            "Ensure cart pages expose containers such as #cart-items or #cart-container for dynamic rendering.",
            "Implement filter, sort, and search flows exactly as defined in their SOPs, including a debounced (~300 ms) search handler for #search-input.",
        ),
    ),
    "css_quality": PromptSection(
        "=== CSS QUALITY BAR ===",
        (
            "Deliver modern styling with subtle shadows (e.g., box-shadow: 0 2px 8px rgba(0,0,0,0.1)), rounded corners, and smooth transitions.",
            "Use CSS Grid or Flexbox to build responsive product grids (3–4 columns desktop, 2 tablet, 1 mobile).",
            "Adopt modern font stacks (-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif) with consistent sizing and line heights.",
            "Design buttons with ample padding, rounded corners, and hover/active transitions.",
            "Maintain generous spacing, padding, and margins to create a clear visual hierarchy, especially around header/footer boundaries.",
        ),
    ),
    "consistency_requirements": PromptSection(
        "=== CONSISTENCY REQUIREMENTS ===",
        (
            "Navigation menus must list every HTML page from FILES on every page.",
            "IDs (#search-input, #cart-count, #cart-subtotal, #products-container) must match exactly between HTML and JavaScript.",
            "Cart summaries in the header must update automatically across all pages via shared JavaScript.",
            "Ensure every DOM element that JavaScript references actually exists on the relevant page.",
            "Always link the same shared CSS and JS assets (e.g., styles.css, script.js) unless file requirements explicitly add alternatives.",
        ),
    ),
    "tool_and_io_rules": PromptSection(
        "=== TOOL & I/O RULES ===",
        (
            "Action Input payloads must be inline JSON with double-quoted keys/values, no Markdown fences, and no trailing commas.",
            "Replace placeholders ([filename], [PROJECT_NAME], [LANGUAGE], etc.) before invoking any tool.",
            "Map programming languages from filenames using the standard extension map (HTML, CSS, JavaScript, TypeScript, Python, etc.).",
            "Include the phrases \"Generate CSS that styles the HTML elements from the previous file\" for CSS queries and \"Generate JavaScript that manipulates HTML elements and uses CSS classes from the previous files\" for JS queries.",
            "Save each generated file immediately after running code_generation_tool; never batch saves.",
            "Verify each saved file with file_reader to ensure there are no ellipses or truncation; regenerate if verification fails.",
            "Before moving to the next file, confirm code_generation_tool was invoked at least once for the current file in this session.",
            "Keep Action names plain text (e.g., \"Action: code_generation_tool\"); never wrap them in Markdown like **Action** or __Action__.",
            "After all files are saved and verified, deliver the Final Answer immediately, explicitly confirm every file was generated this session via code_generation_tool, avoid creating extra files, and stop. If a step cannot be completed, reply with \"ERROR: Engineer could not complete the required actions.\"",
        ),
    ),
    "process_guardrails": PromptSection(
        "=== PROCESS GUARDRAILS ===",
        (
            "Observations from code_generation_tool are raw strings—strip markdown fences and extract only the code before saving.",
            "Preserve whitespace and newlines exactly; never replace sections with ellipses or summaries.",
            "If code extraction fails or appears incomplete, rerun code_generation_tool instead of saving partial output.",
            "Pass the extracted code string directly to save_file_code (not JSON-stringified).",
            "Keep styling in CSS files and behavior in JavaScript; HTML should only contain structure and semantic content.",
        ),
    ),
}

DEFAULT_SECTION_ORDER = (
    "project_alignment",
    "react_sequence",
    "html_structure",
    "product_data",
    "javascript_behavior",
    "css_quality",
    "consistency_requirements",
    "tool_and_io_rules",
    "process_guardrails",
)


def render_prompt_sections(section_keys: Iterable[str] | None = None) -> str:
    """Render prompt sections in the requested order."""

    keys = section_keys or DEFAULT_SECTION_ORDER
    rendered_sections: list[str] = []
    for key in keys:
        section = PROMPT_SECTIONS.get(key)
        if section:
            rendered_sections.append(section.render())
    return "\n\n".join(rendered_sections)


SOP_REFERENCE_TEXT = (
    "Full SOP templates live in nat_mas_agents.sop_templates (HEADER, FOOTER, CART, FILTER, SORT, SEARCH, INTEGRATION). "
    "Reference them as needed instead of embedding their entire contents in the engineer brief."
)

