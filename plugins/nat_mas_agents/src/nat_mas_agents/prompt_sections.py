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
            "Headers need a clickable logo linking to index.html (use relative paths like 'index.html', 'shop.html', 'cart.html', 'checkout.html', 'about.html', NOT absolute paths).",
            "Headers must include navigation menu with links to ALL pages, explicitly including shop.html, cart.html, checkout.html, and about.html.",
            "Headers need #search-input on the input element, and a cart summary using #cart-count and #cart-subtotal.",
            "Footers must show company info, navigation links to all pages, contact info, and copyright with a dark (#343a40) background.",
            "Do not use inline styles or <style> tags; keep HTML presentation-free and link shared CSS/JS assets exactly as named.",
            "NAMING CONTRACT (CRITICAL): All shared header/footer/product grid elements MUST use the canonical BEM-style class names defined by the MAS prompts; HTML MUST NOT introduce parallel synonyms (e.g., .site-header, .top-nav) for the core layout structure. The canonical classes include (non-exhaustive): header, header__container, header__logo, header__nav, header__nav-list, header__nav-item, header__nav-link, header__search, header__search-input, header__cart, header__cart-link, header__cart-icon, header__cart-count, header__cart-subtotal, footer, footer__container, footer__about, footer__nav, footer__social, footer__bottom, products, products__container, product-card and its __image/__info/__title/__price/__category/__description/__actions modifiers.",
            "CRITICAL: Product listing pages (index.html, shop.html) MUST include visible filter and sort controls above the product container:",
            "  - Filter dropdown: select element with id='filter-select' or id='category-filter' with options for all categories plus 'All' option",
            "  - Sort dropdown: select element with id='sort-select' or id='sort-by' with options (Price: Low to High, Price: High to Low, Name: A-Z, Name: Z-A)",
            "  - These controls must be present in HTML so JavaScript can attach event listeners to them.",
            "CRITICAL: Product listing pages MUST have empty container id=\"products-container\" (products loaded from JSON, NEVER hardcoded in HTML).",
            "CRITICAL: Provide checkout.html with shared header/footer, an order summary region (e.g., #checkout-summary), shipping/payment/contact forms (e.g., #checkout-form), and a prominent Place Order button; this page must pull totals from CartManager/localStorage.",
            "CRITICAL: Provide about.html that reuses the shared header/footer and showcases brand story, mission, sustainability highlights, team/contact info, and CTAs back to shop/cart.",
            "CRITICAL: Provide cart.html containers (#cart-items, #cart-empty, #cart-subtotal/#cart-total, checkout CTA) so JavaScript can render every cart line item from localStorage—never hardcode rows or totals.",
            "Reference shared CSS via <link rel=\"stylesheet\" href=\"styles.css\"> (or the specified filename) and place <script src=\"script.js\"></script> immediately before </body>—never after </html>.",
            "Avoid fixed-position footers unless additional bottom padding prevents overlap.",
            "ADVANCED: Include comprehensive accessibility attributes (aria-labels, aria-live, roles, tabindex) for screen readers.",
            "ADVANCED: Add Schema.org microdata or JSON-LD structured data for products, organization, and breadcrumbs for SEO.",
            "ADVANCED: Include loading states and skeleton screens for dynamic content (use data-loading attributes).",
            "ADVANCED: Add modal dialog structures with proper ARIA attributes (role=\"dialog\", aria-modal=\"true\", aria-labelledby).",
            "ADVANCED: Use semantic HTML5 elements (<header>, <nav>, <main>, <section>, <article>, <footer>, <aside>, <figure>, <figcaption>).",
            "ADVANCED: Use responsive images with srcset and sizes attributes, and <picture> element for art direction.",
            "ADVANCED: Add proper meta tags for SEO (Open Graph, Twitter Cards, canonical URLs, description, keywords).",
        ),
    ),
    "product_data": PromptSection(
        "=== PRODUCT & ASSET HANDLING ===",
        (
            'CRITICAL: products.json (in SHARED_ASSETS) plus an empty HTML container id="products-container" power all product listings; NEVER hardcode cards in HTML.',
            "JavaScript renders into #products-container by fetching products.json (array or {products}) and showing graceful fallbacks on errors.",
            "Every product entry includes id, name, price, category, description, and image; keep SHARED_ASSETS filenames (styles.css, script.js, products.json, etc.) exact.",
        ),
    ),
    "javascript_behavior": PromptSection(
        "=== JAVASCRIPT BEHAVIOR ===",
        (
            "Load products.json on DOMContentLoaded, render dynamic cards (with data-category/data-price), and surface helpful error UI when fetch fails.",
            "Cart logic lives in localStorage key \"cart\"; call updateCartDisplay() after every mutation and on load so #cart-count/#cart-subtotal stay in sync.",
            "Attach listeners only when matching elements exist (search input, filters, sort, add-to-cart, cart controls) and gate behavior per active page.",
            "Cart/detail pages must expose containers such as #cart-items or #cart-container for dynamic rendering.",
            "Implement search, filter, and sort exactly per SOP (debounced ~300 ms search on #search-input).",
        ),
    ),
    "css_quality": PromptSection(
        "=== CSS QUALITY BAR ===",
        (
            "Deliver modern, responsive layouts: CSS Grid for #products-container (1/2/3/4 columns from mobile → large) plus generous spacing and smooth transitions.",
            "Product cards: flex-column layout, aspect-ratio image wrapper, hover elevation/zoom, footer aligning price + button, optional badges/loading states.",
            "Adopt a coherent design system (CSS variables, modern font stack, meaningful BEM classes, focus-visible states) and keep buttons/links polished.",
            "Define global design tokens, resets, containers, and utility classes so header, hero, filters, cards, cart, and checkout share one cohesive aesthetic.",
            "Style all shared layout components (header/footer/product grid/shop controls) primarily via the canonical BEM-style classes defined in the naming contract. Avoid creating competing top-level selectors like .site-header or .primary-nav that do not appear in the HTML; instead, extend the canonical classes with modifiers if needed.",
            "Cover every shared component: sticky header/nav, hero banner, filter/sort/search toolbar, product grid, cart table, checkout forms, modals/toasts, and badges—include dark-mode + prefers-reduced-motion guardrails.",
            "Advanced polish (optional): gradients/glassmorphism/backdrop-filter, fluid clamp() spacing, micro-animations, skeleton shimmer, tooltips/dropdowns with layered z-index control.",
        ),
    ),
    "consistency_requirements": PromptSection(
        "=== CONSISTENCY REQUIREMENTS ===",
        (
            "Use identical header/footer/nav structures across ALL HTML pages (links to every file) and keep shared asset paths uniform.",
            "IDs that JavaScript expects (#search-input, #cart-count, #cart-subtotal, #products-container, cart containers, etc.) must exist verbatim.",
            "Before shipping a page, cross-check that every JS selector maps to a real element on that page so shared logic never no-ops.",
            "For each shared component (header, footer, product cards, shop controls), ensure at least one HTML file and styles.css both reference the same canonical class names; if a class appears only in CSS or only in HTML for a shared component, revise the code until they match.",
        ),
    ),
    "tool_and_io_rules": PromptSection(
        "=== TOOL & I/O RULES ===",
        (
            "Action Input payloads must be inline JSON with double-quoted keys/values, no Markdown fences, and no trailing commas.",
            "Replace placeholders ([filename], [PROJECT_NAME], [LANGUAGE], etc.) before invoking any tool.",
            "Map programming languages from filenames using the standard extension map (HTML, CSS, JavaScript, TypeScript, Python, etc.).",
            "Include the phrases \"Generate CSS that styles the HTML elements from the previous file\" for CSS queries and \"Generate JavaScript that manipulates HTML elements and uses CSS classes from the previous files\" for JS queries.",
            "Run the loop Thought → code_generation_tool → Thought → save_file_code per file (no batching), keep action labels plain text, and confirm completion in the Final Answer.",
            "Use file_reader to spot truncation when needed; regenerate instead of shipping partial output.",
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

