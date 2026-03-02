# SPDX-FileCopyrightText: Copyright (c) 2025, NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
#
# Lightweight web-generation policy layer for MAS V2.
#
# Goal: reintroduce strong structural bias (naming contract, component
# responsibilities, DOM/CSS/JS conventions) without inlining the very
# large SOP text from the legacy MAS.
#
# This module is intentionally compact and focused on:
# - Naming contract (class names and IDs)
# - Component responsibilities (header, footer, product card, cart)
# - High-level CSS/JS behavior expectations
#
from __future__ import annotations

from typing import Iterable, List


HEADER_POLICY = """
WEB HEADER POLICY (SHARED ACROSS PAGES)
- Header appears on EVERY page with consistent structure.
- Required classes:
  - .header           → top-level header container
  - .header__logo     → brand name / logo, links to index.html
  - .header__nav      → main navigation container
- Required IDs:
  - #search-input     → text input for searching products/content
  - #cart-count       → span showing number of items in cart
  - #cart-subtotal    → span showing subtotal amount
- Behavior expectations:
  - Navigation links cover ALL main pages (index.html, shop.html, product-detail.html, cart.html, etc.) using <a href="..."> links.
  - Do NOT leave .header__nav as only a bare <select> or a single control; even if filters exist, keep a visible page navigation menu.
  - Filters (#category-filter) and sorting (#sort-by) controls should live in a dedicated toolbar/section on listing pages (e.g. above #products-container), not as the only content of the main nav.
  - Header is responsive: horizontal on desktop, stacked on small screens.
""".strip()


PRODUCT_CARD_POLICY = """
PRODUCT CARD / GRID POLICY
- Class names for product listing:
  - .product-card                → clickable product tile
  - .product-card__title         → product name
  - .product-card__price         → price text
  - .product-card__description   → short description text
- Container on shop-like pages:
  - #products-container          → root element that holds product cards (use ID selector in CSS: #products-container)
- Behavior expectations:
  - Cards are laid out in a responsive grid: 3 columns on desktop, down to 1 on small screens.
  - Each card has clear hover and focus styles (e.g., subtle shadow, border, or scale) so it feels interactive.
  - Empty state is handled: when there are no products to show, display a friendly message instead of an empty grid.
  - Each product card MUST include a link to the product detail page: product-detail.html?id=<product.id> (e.g. "View details" or wrap the card).
""".strip()


HOME_PAGE_POLICY = """
HOME / LANDING PAGE POLICY (index.html)
- index.html is a proper landing page, not just a bare grid container.
- Above the product grid, include a hero section with:
  - A prominent <h1> heading that clearly states the store or site's value.
  - 1–3 short sentences of supporting copy (what this site offers, who it is for).
  - A primary call-to-action button (e.g. "Shop now", "Browse collection") that links to the main listing page (often shop.html).
- Below the hero, include at least one additional content section such as:
  - Featured categories or featured products.
  - Benefits / trust signals (e.g. free shipping, secure checkout, 24/7 support).
  - Highlighted collections or promotions.
- Even if products are loaded dynamically into #products-container, the static HTML MUST still include headings and layout wrappers so the page feels complete and production-ready.
""".strip()


RESPONSIVE_LAYOUT_POLICY = """
RESPONSIVE LAYOUT POLICY (CSS)
- Layout adjusts smoothly from 3 columns on desktop → 2 columns on tablet → 1 column on small screens.
- Use CSS Grid or Flexbox, do NOT rely on tables.
- The product grid container uses id="products-container" in HTML; CSS MUST target #products-container (e.g. #products-container { display: grid; grid-template-columns: repeat(3, 1fr); ... }).
- Define clear breakpoints (at minimum: 1024px, 768px, 480px) and adjust:
  - Header layout (nav wrapping / stacking, search/cart moving below logo on small screens)
  - Product grid columns (3 → 2 → 1) via #products-container
  - Spacing, font sizes, and paddings so content remains readable.
- Use lightweight transitions (e.g., transition: all 0.2s ease-in-out) on hoverable elements for a polished feel.
""".strip()


CSS_QUALITY_POLICY = """
CSS QUALITY – PRODUCTION-GRADE STYLES (not minimal)
- Use :root CSS variables for: primary/secondary colors, background and text colors, border color, box shadows (e.g. --shadow-sm, --shadow-md), border-radius (--radius-sm, --radius-md), spacing (optional: clamp for fluid spacing), font families, transition duration (e.g. --transition-base: 0.2s ease). This keeps the design consistent and easy to theme.
- Base styles: html { scroll-behavior: smooth }; body { min-height: 100vh, use var() for font and colors }; main { max-width container (e.g. 1200px), margin auto, padding }; a:hover, a:focus-visible { distinct color }; img { display: block; max-width: 100%; height: auto }; button { cursor: pointer }; button:disabled { opacity: 0.6 }; form controls (input, select) with font-family: inherit and focus-visible outline.
- Header: use position: sticky and z-index so it stays on top; optional box-shadow or border-bottom; .header__nav a with padding, border-radius, transition; :hover and :focus-visible (and optionally [aria-current="page"]) with distinct background/color so nav links feel interactive.
- Product cards: .product-card with box-shadow (e.g. var(--shadow-sm)), border-radius, transition for transform and box-shadow; :hover with transform (e.g. translateY(-4px)) and stronger box-shadow; optional ::after overlay for hover glow. Style .product-card__title, .product-card__price, .product-card__description clearly. Buttons inside cards (.product-card__button or button) with background, border-radius, padding, and :hover/:focus-visible (e.g. translateY(-2px), box-shadow). If the design has product images, use an image wrapper with aspect-ratio (e.g. 4/3) and overflow: hidden; img with object-fit: cover and optional hover scale.
- Footer: padding and border-top; optional multi-column layout with .footer__section; footer links with :hover/:focus-visible.
- Cart: .cart-item with flex/grid, padding, border-bottom; #cart-total or .cart-total with font-weight and margin-top.
- Accessibility: use :focus-visible (not just :focus) for keyboard focus states; optional @media (prefers-reduced-motion: reduce) to shorten or disable transitions/animations.
- Coverage expectation: do not stop after a handful of flat rules. A production stylesheet should cover at least: base/body, header/nav/search/cart, hero/landing sections, filters/sort/search toolbar, #products-container grid, .product-card and its sub-elements, cart list + summary, product-detail layout, and footer, plus responsive breakpoints. It is acceptable (and preferred) that the CSS file is long if it makes the UI feel like a complete app rather than a wireframe.
""".strip()


SHOP_BEHAVIOR_POLICY = """
SHOP & SEARCH BEHAVIOR POLICY (JS)
- Live search:
  - Input: #search-input
  - Filters products by name/description as user types (case-insensitive).
  - Empty state: when no products match the search term, render a clear message (e.g., "No products found for this search") instead of an empty list.
- Category filtering:
  - Select element with id="category-filter" or "filter-select".
  - Filters by product.category; "all" shows everything.
- Sorting:
  - Select element with id="sort-by" or "sort-select".
  - Supports at least: price-asc, price-desc, name-asc, name-desc.
- CRITICAL – Optional elements: #category-filter and #sort-by exist ONLY on shop.html. Before calling addEventListener on them, check that the element exists (e.g. if (categoryFilter) categoryFilter.addEventListener(...)). Otherwise the script will throw on index, cart, or product-detail pages.
- Implementation:
  - Use modern ES6+ (const/let, arrow functions, array methods).
  - No external libraries; vanilla JavaScript only.
""".strip()


CART_POLICY = """
CART & LOCALSTORAGE POLICY (JS)
- Cart storage:
  - Use localStorage key "cart".
  - Structure: { items: [{ id, name, price, quantity, ... }] }.
- Required behaviors:
  - Add to cart from product listing/detail.
  - Update quantity, remove items, compute totals on cart.html.
  - Update header (#cart-count, #cart-subtotal) on every page load.
  - Cart page HTML must include #cart-items (container for list) AND #cart-total (element showing total amount). updateCartDisplay() must update both #cart-items and #cart-total when present.
- ID consistency: product id in JSON may be number; data-id in HTML is string. When comparing (e.g. item.id === productId), use consistent type: e.g. Number(productId) or String(item.id) so add-to-cart and remove work correctly.
- Optional element: #cart-items exists only on cart.html. Guard: if (cartItemsContainer) { ... } before updating its innerHTML, so other pages do not throw.
- Implementation notes:
  - Always guard against missing/invalid localStorage data.
  - Expose a reusable function updateCartDisplay() used after every change.
""".strip()


JS_QUALITY_POLICY = """
JAVASCRIPT QUALITY – STRUCTURE & ROBUSTNESS
- Use modern ES6+ throughout:
  - const/let, arrow functions, template literals, array methods (map/filter/reduce), async/await for fetch.
  - Optional but recommended: small manager-style objects/classes (e.g. ProductManager, CartManager) so listing logic, cart logic, and detail-page logic are not all in one giant function.
- Separation of concerns:
  - One clear block of logic for: loading data (fetch + error handling), rendering lists/cards, wiring filters/sort/search, and cart operations.
  - Avoid deeply nested anonymous callbacks; prefer named functions or methods.
- Defensive DOM access:
  - ALWAYS read elements with querySelector / getElementById and check they exist before using them.
  - For optional elements (filters, sort, cart list, detail containers), guard every event listener and DOM write with an if (el) check.
- Error handling & empty states:
  - Wrap fetch('products.json') in try/catch or .catch; on error, log a clear message and render a friendly fallback in the UI instead of leaving the page blank.
  - For empty product lists or filtered results, render a visible message (“No products found…”) rather than an empty container.
- URL & state handling:
  - Use URLSearchParams to read query parameters (e.g. ?id=, ?q=).
  - Keep cart state in localStorage and always rehydrate header counters and cart views from it on page load.
- Code readability:
  - Use meaningful function and variable names (loadProducts, renderProducts, applyFilters, updateCartDisplay, handleSearchInput, etc.).
  - Keep individual functions short and focused; avoid duplicating logic across listing, detail, and cart views.
""".strip()


PRODUCT_DETAIL_POLICY = """
PRODUCT DETAIL PAGE POLICY (JS + HTML)
- product-detail.html shows one product; the product id comes from the URL query: ?id=1 (e.g. URLSearchParams.get('id')).
- app.js MUST: (1) detect when the current page is product-detail (e.g. pathname contains 'product-detail'); (2) read id from URL (URLSearchParams); (3) find the product in the loaded products array; (4) render name, description, price, image into #product-detail (or .product-detail__specs, .product-detail__image); (5) wire #add-to-cart button to add that product to cart and optionally redirect to cart or show feedback.
- If id is missing or product not found, show a friendly message (e.g. "Product not found") and do not leave the page blank.
- Product listing pages (index, shop) must link to product-detail.html?id=<product.id> so users can open the detail page.
""".strip()


# Single source of truth for class/id so HTML, CSS, and JS stay in sync.
DOM_CLASS_ID_CONTRACT = """
DOM / CLASS & ID CONTRACT (use exactly these names in HTML, CSS, and JS)
- Header (every page):
  - .header, .header__logo, .header__nav
  - #search-input, #cart-count, #cart-subtotal
- Product listing (shop, homepage featured):
  - #products-container  (root for product cards)
  - .product-card, .product-card__title, .product-card__price, .product-card__description
- Shop filters:
  - #category-filter (select), #sort-by (select)
- Cart page:
  - #cart-items (container), .cart-item (each row), #cart-total
- Product detail page:
  - #product-detail (container), .product-detail__image, .product-detail__specs, #add-to-cart
- Footer:
  - .footer
""".strip()


PRODUCTS_JSON_POLICY = """
PRODUCTS DATA (products.json)
- Store ALL product data in a single file: products.json (in the same directory as index.html).
- Format: { "products": [ { "id", "name", "description", "category", "price", "image" } ] }.
- JavaScript MUST load products via fetch: fetch('products.json').then(r => r.json()).then(data => ...).
- Do NOT hardcode the products array inside app.js or HTML. Only products.json holds the list.
- All pages that show products (index, shop, product-detail) use this loaded data.
""".strip()


def _join_blocks(blocks: Iterable[str]) -> str:
    return "\n\n".join(b.strip() for b in blocks if b and b.strip())


def get_architect_web_policy() -> str:
    """Policy text for Architect: full component & naming contract.

    Architect uses this to decide:
    - Which components exist (header, product grid, cart)
    - Which class/ID names must appear in DOM / CSS
    - How files split responsibilities (HTML vs CSS vs JS)
    - products.json in file_structure; JS loads products from it.
    """
    return _join_blocks(
        [
            "=== WEB GENERATION POLICY (ARCHITECT) ===",
            DOM_CLASS_ID_CONTRACT,
            HEADER_POLICY,
            PRODUCT_CARD_POLICY,
            HOME_PAGE_POLICY,
            RESPONSIVE_LAYOUT_POLICY,
            CSS_QUALITY_POLICY,
            SHOP_BEHAVIOR_POLICY,
            CART_POLICY,
            JS_QUALITY_POLICY,
            PRODUCT_DETAIL_POLICY,
            PRODUCTS_JSON_POLICY,
        ]
    )


def get_dom_contract_for_design_spec() -> str:
    """DOM and products.json contract to inject into design_spec so Worker/Planner see it."""
    return _join_blocks(
        [
            DOM_CLASS_ID_CONTRACT,
            PRODUCTS_JSON_POLICY,
            "JS RULES: (1) Guard optional elements: only use #category-filter, #sort-by, #cart-items if element exists. "
            "(2) Product detail: read ?id= from URL, render product, wire #add-to-cart. (3) Cart page must have #cart-total; update it in updateCartDisplay(). "
            "(4) Product cards must link to product-detail.html?id=<id>. (5) Use consistent id type (Number/String) when comparing for cart.",
        ]
    )


def get_policy_for_target_files(target_files: List[str]) -> str:
    """Return a focused policy snippet for the given target files.

    Worker should NOT see the entire policy every step – only what is
    relevant for the file(s) being implemented.
    """
    if not target_files:
        return ""

    # Normalize names (strip directories, lowercase for matching)
    names = []
    for raw in target_files:
        name = (raw or "").strip().replace("\\", "/")
        if "/" in name:
            name = name.split("/")[-1]
        names.append(name.lower())

    blocks: List[str] = ["=== WEB GENERATION POLICY (THIS FILE) ==="]

    # Always include DOM contract when editing any web asset so class/id stay consistent
    if any(
        n.endswith(".html") or n.endswith(".css") or n.endswith(".js") or n == "products.json"
        for n in names
    ):
        blocks.append(DOM_CLASS_ID_CONTRACT)

    if any(n.endswith(".css") for n in names):
        blocks.append(HEADER_POLICY)
        blocks.append(PRODUCT_CARD_POLICY)
        blocks.append(RESPONSIVE_LAYOUT_POLICY)
        blocks.append(CSS_QUALITY_POLICY)

    if any(n.endswith(".js") for n in names):
        blocks.append(PRODUCTS_JSON_POLICY)
        blocks.append(SHOP_BEHAVIOR_POLICY)
        blocks.append(CART_POLICY)
        blocks.append(PRODUCT_DETAIL_POLICY)
        blocks.append(JS_QUALITY_POLICY)

    if any(n.endswith(".html") for n in names):
        blocks.append(HEADER_POLICY)
        blocks.append(PRODUCT_CARD_POLICY)
        if any("index.html" in n or n == "index" for n in names):
            blocks.append(HOME_PAGE_POLICY)
    if any("product-detail" in n for n in names):
        blocks.append(PRODUCT_DETAIL_POLICY)

    if "products.json" in names:
        blocks.append(PRODUCTS_JSON_POLICY)

    # If we didn't add anything specific, don't spam the prompt.
    if len(blocks) == 1:
        return ""

    return _join_blocks(blocks)

