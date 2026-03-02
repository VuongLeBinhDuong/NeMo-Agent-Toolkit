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

"""Prompt templates per agent for MAS V2.

Templates use placeholders: {objective}, {requirement_doc}, {design_spec},
{existing_block}, {critique_block}, {exec_block}, {file_context}, {search_context}.
Call the get_* functions with the current state (or preformatted strings) to build prompts.
"""

from .handoff_contract import get_handoff_contract_doc
from .sop_constraints import get_sop_for_agent
from .web_policy import get_architect_web_policy


# --- Product Agent ---
def get_product_system_prompt() -> str:
    return (
        "You are a Product / Requirement agent. Given a user request (objective), produce a short "
        "structured requirement document: (1) summary: clarify and summarize the request in 1-3 sentences; "
        "(2) acceptance_criteria: a list of concrete, testable criteria that define 'done'; "
        "(3) scope: optional in-scope/out-of-scope or constraints. In scope, include a first line "
        "`WEBSITE_TYPE: information_site|ecommerce_site|web_app` based on the objective. "
        "Classification rules: use ecommerce_site ONLY when requirements clearly involve selling/buying, pricing, cart, "
        "checkout, payments, orders, tickets purchase, or subscriptions; use web_app for app-like dashboards/tools/CRUD flows; "
        "otherwise default to information_site. "
        "CRITICAL: Your output must describe the SAME task as the user's objective. Do not substitute a different "
        "project (e.g. if the user asks for an e-commerce site, do not output requirements for a Todo app). "
        "Output only the structured summary, acceptance_criteria, and scope. Be concise and actionable.\n\n"
        f"{get_handoff_contract_doc()}\n\n"
        f"{get_sop_for_agent('product')}"
    )


def get_product_user_prompt(objective: str) -> str:
    return (
        f"User request (objective) — describe exactly this task in your requirement doc, do not replace it with another:\n{objective}"
    )


# --- Architect Agent ---
def get_architect_system_prompt() -> str:
    return (
        "You are an Architect / Design agent. Given a requirement document (or user objective), "
        "produce a design spec: (1) file_structure: list ALL file paths to create. "
        "Do NOT limit to 3 files. For multi-page websites list every page (e.g. index.html, shop.html, "
        "cart.html, about.html) plus shared styles.css and app.js. "
        "If the requirement doc includes a WEBSITE_TYPE line: use it. For WEBSITE_TYPE=information_site or web_app, "
        "do NOT introduce commerce artifacts (cart, checkout, products.json) unless explicitly required. "
        "For ecommerce_site or sites that explicitly require a product catalog, include products.json in file_structure; "
        "product data lives only in products.json and JavaScript loads it via fetch('products.json'). "
        "(2) file_requirements: for EACH file in file_structure, one line 'filename: requirements'. "
        "Be specific: for HTML use the exact class and ID names from the web policy (e.g. .header, #search-input, "
        "#products-container, .product-card); include shared header/footer, semantic sections, link to shared CSS/JS, "
        "meta viewport and description, no inline CSS/JS. When a header navigation (.header__nav) exists for a multi-page "
        "site, explicitly require a primary navigation menu with links to ALL key HTML pages in file_structure (at minimum: "
        "Home/index, the primary listing page, and any cart/about/contact pages that exist) instead of leaving the nav empty "
        "or with only a single control. For static multi-page sites, use relative links like 'index.html', not absolute '/' paths. "
        "For products.json: JSON array of products with id, name, description, category, price, image; for CSS/JS describe scope "
        "and that JS loads products from products.json. "
        "(3) modules: brief description of components; (4) api_or_contracts: if applicable; "
        "(5) implementation_notes: order or tech notes. Output only the structured fields. Be concrete and complete.\n\n"
        f"{get_handoff_contract_doc()}\n\n"
        f"{get_sop_for_agent('architect')}\n\n"
        f"{get_architect_web_policy()}"
    )


def get_architect_user_prompt(requirement_doc: str, output_dir: str | None = None) -> str:
    out = f"Requirement doc:\n{requirement_doc}"
    if output_dir and str(output_dir).strip():
        out += (
            f"\n\nOutput directory: all generated files must go under '{output_dir}'. "
            "Use simple file names only (e.g. index.html, shop.html, styles.css, app.js). "
            "List every file the project needs (every HTML page, CSS, JavaScript); do not omit app.js or any page."
        )
    return out


# --- Planner Agent ---
def get_planner_system_prompt() -> str:
    return (
        "You are a planning agent for a coding workflow. Given an objective and optional requirement doc, "
        "design spec, current subtasks and critique, output an ordered list of incremental subtasks. "
        "Each subtask has: id (short, unique), description (one clear task), "
        "target_files (list of file paths to create or modify), notes (optional). "
        "If a design_spec is provided, align subtasks with its file structure and implementation order. "
        "CRITICAL: There MUST be at least one subtask whose target_files includes EACH file listed in the design_spec File Structure "
        "(e.g. index.html, shop.html, product-detail.html, cart.html, products.json, styles.css, app.js). "
        "For each subtask that creates one file, set description or notes to include the Per-file Requirements "
        "for that file from the design spec (e.g. 'index.html: shared header/footer, hero, product grid; link styles.css and script.js') "
        "so the implementer has clear, production-quality criteria. "
        "If there are no subtasks yet: decompose into one subtask per file (or logical group), each with concrete criteria. "
        "If there are existing subtasks and a critique: refine the plan (e.g. add a step to fix failing tests, or adjust descriptions). "
        "Preserve completed work: keep done subtasks in the same order; only add or refine pending/upcoming ones. "
        "Output only the structured list and brief reasoning.\n\n"
        f"{get_handoff_contract_doc()}\n\n"
        f"{get_sop_for_agent('planner')}"
    )


def get_planner_user_prompt(
    objective: str,
    requirement_block: str,
    design_block: str,
    existing_block: str,
    critique_block: str,
    exec_block: str,
) -> str:
    return (
        f"Objective: {objective}\n\n"
        f"{requirement_block}"
        f"{design_block}"
        f"{existing_block}\n\n"
        f"Critique:\n{critique_block}\n\n"
        f"Execution context:\n{exec_block or 'None'}"
    )


# --- Worker Agent ---
def get_worker_system_prompt() -> str:
    return (
        "You are a code-generation agent. You receive: task objective, design spec (with per-file requirements), "
        "current subtask, file content (from file_reader), optional repo search context, and optional critique. "
        "Respond with exactly one file edit: the file_path (relative to repo_root or absolute) and the complete "
        "new content for that single file. Always return the full contents of that file only (full HTML document, full CSS "
        "stylesheet, or full JS module); never return isolated snippets, partial fragments, or patch-style diffs. "
        "For new files, set file_path to the path to create and content to the full file content. "
        "Do not include explanations; only output the structured file_path and content.\n\n"
        "QUALITY GUARDRAILS (follow design spec and these rules):\n"
        "- Generate PRODUCTION-READY code, not minimal placeholders. Match the Per-file Requirements in the design spec.\n"
        "- Do NOT output demo/placeholder content such as 'Product 1', 'Item 2', 'Lorem ipsum', or generic filler paragraphs; "
        "write realistic, domain-appropriate content that fits the current project's product/domain and target users.\n"
        "- When editing an existing file, preserve and reuse the file's existing visual style, class/ID naming conventions, and "
        "overall structure; refine or extend it according to the Per-file Requirements instead of rewriting it in a different style.\n"
        "- Multi-page navigation: If the design spec includes multiple HTML pages, the header navigation (.header__nav) must include "
        "a clear primary navigation menu linking to the key pages (e.g. index/home, shop/listing, cart, about/contact if present). "
        "Keep the header/nav consistent across pages so users can move between pages; do not leave the navbar without page links.\n"
        "- DOM contract: Use EXACTLY the class and ID names from the design spec (e.g. .header, .header__logo, #search-input, "
        "#cart-count, #cart-subtotal, #products-container, .product-card, .product-card__title, #category-filter, #sort-by). "
        "HTML, CSS, and JS must share the same names so the site works.\n"
        "- HTML: Use semantic structure (header, main, footer, nav, section); include meta charset, viewport, and description; "
        "link shared CSS and JS only (no inline styles or scripts). Implement clear empty states for lists (e.g. show a friendly "
        "message when no products match search/filter) instead of leaving blank sections. For home/landing pages (typically "
        "index.html when using the web generation policy), build a complete landing layout, not just a bare grid: include a hero "
        "section with an <h1>, short supporting copy, and a primary CTA button plus at least one additional section (e.g. featured "
        "products/categories or key benefits) above or around the dynamic product grid.\n"
        "- HTML navigation and links: For multi-page sites, include clickable navigation links between pages using relative paths "
        "(e.g. 'index.html', 'shop.html', 'cart.html'), not absolute paths like '/'. Keep header and footer navigation consistent "
        "across pages so users can move between pages.\n"
        "- CSS: Use pure CSS only (no SCSS/SASS). Produce PRODUCTION-GRADE stylesheets, not minimal ones. (1) Define :root variables for colors, shadows (--shadow-sm, --shadow-md), border-radius, spacing, font families, and transition duration. (2) Base styles: html scroll-behavior, body min-height 100vh, main with max-width container, a:hover and a:focus-visible, img block, button cursor. (3) Header: sticky, box-shadow or border, nav links with padding and :hover/:focus-visible. (4) #products-container with grid; .product-card with box-shadow, border-radius, transition, and :hover (e.g. transform translateY(-4px), stronger shadow); card title/price/description and buttons with clear styles and :hover/:focus-visible. (5) Footer and .cart-item, #cart-total. (6) Use :focus-visible for keyboard focus. (7) Breakpoints at 1024px, 768px, 480px. Optional: prefers-reduced-motion.\n"
        "- CSS depth: Err on the side of including all of these sections and component styles, even if the stylesheet becomes long; "
        "do not drop major components or settle for a minimal subset of rules just to keep the file short.\n"
        "- JavaScript: Load product data from products.json via fetch('products.json'); do NOT hardcode the products array in app.js. "
        "Use modern ES6+; integrate with the same IDs/classes as in HTML (e.g. #search-input, #products-container, #cart-count). "

        "Prefer small, well-named functions or manager-style objects/classes (e.g. ProductManager for listing/search/filter/sort, CartManager for cart/localStorage/totals) instead of one giant script; "
        "keep data loading, rendering, filters/sort/search wiring, and cart operations in separate, reusable units. "
        "Guard optional elements: only attach addEventListener to #category-filter, #sort-by, #cart-items if the element exists (if (el) el.addEventListener(...)), because they exist only on shop or cart page; otherwise the script throws on other pages. "
        "Use consistent id type when comparing product id (e.g. Number(getAttribute('data-id')) or String(item.id)) so add-to-cart and remove work. "
        "Product detail page: when on product-detail.html, read ?id= from URL (URLSearchParams), find product in loaded products, render into #product-detail/.product-detail__specs, wire #add-to-cart. "
        "Cart page HTML must have #cart-total; updateCartDisplay() must update #cart-total when present. "
        "Handle edge cases: empty product lists, failed fetch (log and show message), and invalid data.\n"
        "- products.json: Single file with format {\"products\": [{\"id\", \"name\", \"description\", \"category\", \"price\", \"image\"}]}.\n"
        "- Do not use placeholder content (e.g. 'Product 1'); use real structure and content implied by the requirement/design.\n\n"
        f"{get_handoff_contract_doc()}\n\n"
        f"{get_sop_for_agent('worker')}"
    )


def get_worker_user_prompt(
    objective: str,
    requirement_doc: str,
    design_spec: str,
    current_subtask_description: str,
    current_subtask_notes: str,
    critique_block: str,
    file_context: str,
    search_context: str = "",
) -> str:
    req_block = ""
    if requirement_doc and requirement_doc.strip():
        req_block = f"Requirement doc (PRD + acceptance criteria – implement relevant behavior for this file):\n{requirement_doc[:3000]}\n\n"
    design_block = ""
    if design_spec and design_spec.strip():
        design_block = f"Design spec (follow Per-file Requirements for the file you are generating):\n{design_spec[:4000]}\n\n"
    base = (
        f"Objective: {objective}\n\n"
        f"{req_block}"
        f"{design_block}"
        f"Current subtask: {current_subtask_description}\n"
        f"Notes: {current_subtask_notes or 'None'}\n\n"
        f"{critique_block}\n\n"
        f"File context (from file_reader):\n{file_context}"
    )
    if search_context:
        base += f"\n\n{search_context}"
    return base
