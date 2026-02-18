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

"""SOP (Standard Operating Procedures) and Templates for default component behaviors.

This module provides standardized specifications for common web components
(header, footer, cart, filter, sort) so agents don't have to guess or
invent implementations. These templates ensure consistency across all
generated projects.
"""

# Website type guidance (used to avoid forcing everything into e‑commerce)
WEBSITE_TYPE_SOP = """
=== WEBSITE TYPE CLASSIFICATION - STANDARD OPERATING PROCEDURE ===

PURPOSE:
- Classify the kind of website requested so downstream agents choose the right structure and SOPs.

SUPPORTED WEBSITE_TYPE VALUES:
- information_site  → Content / information focused (e.g., news, schedules, results, blogs, documentation).
- ecommerce_site    → Selling products/tickets with cart, checkout, orders, payments.
- web_app           → Application-style UI (dashboards, tools, forms, auth-heavy apps).

CLASSIFICATION RULES:
- Use "ecommerce_site" ONLY when requirements clearly mention selling, buying, pricing, cart, checkout, payment, orders, tickets purchase, subscriptions, or similar commerce flows.
- Use "web_app" when the focus is on interactive tools, dashboards, data entry, CRUD apps, or authenticated workflows, not primarily on content or shopping.
- In all other cases (pure content, listings, schedules, results, news, articles), default to "information_site".
- For "information_site", DO NOT introduce cart, checkout, products.json, or pricing unless the requirements explicitly ask for commerce features.

USAGE BY AGENTS:
- Product Manager MUST write a line "WEBSITE_TYPE: [information_site|ecommerce_site|web_app]" in the specification file.
- Architect and Project Manager MUST preserve this WEBSITE_TYPE line in their outputs.
- Engineer MUST read WEBSITE_TYPE from the project plan and:
  - For ecommerce_site → apply full SHOP/CART/PRODUCTS/CHECKOUT SOPs.
  - For information_site → avoid introducing cart/checkout/products.json; focus on informational pages (e.g., index, matches, results, about) and optional search/filter/sort for content.
  - For web_app → follow general coding constraints but do NOT assume cart/checkout/products.json unless FILE_REQUIREMENTS explicitly mention them.
"""

# Standard Header Component Specification
HEADER_SOP = """
=== HEADER COMPONENT - STANDARD OPERATING PROCEDURE ===

CRITICAL: Header MUST appear on EVERY HTML page with IDENTICAL structure and IDs.

WEBSITE_TYPE-SPECIFIC REQUIREMENTS:

For ecommerce_site:
- Logo/Brand Name: Left-aligned, clickable (links to homepage/index.html)
- Navigation Menu: Horizontal links to ALL pages listed in FILES (e.g., Home, Shop, Cart, Checkout, About)
- Search Bar: Input field with id="search-input" (MUST be on the input element itself, not a wrapper div), placeholder="Search products..."
- Cart Section: Right-aligned, showing:
  * Item count: <span id="cart-count">0</span> items
  * Subtotal: $<span id="cart-subtotal">0.00</span>
  * Optional: Clickable to navigate to cart page

For information_site or web_app:
- Logo/Brand Name: Left-aligned, clickable (links to homepage/index.html)
- Navigation Menu: Horizontal links to ALL pages listed in FILES (e.g., Home, Matches, Results, About) - DO NOT include shop/cart/checkout unless explicitly required
- Search Bar: Input field with id="search-input" (MUST be on the input element itself, not a wrapper div), placeholder="Search..." (domain-appropriate placeholder)
- NO Cart Section: Do NOT include cart-count, cart-subtotal, or cart links unless explicitly required

REQUIRED HTML STRUCTURE (must be identical on ALL pages):

For ecommerce_site:
<header>
  <div class="header-container">
    <a href="index.html" class="logo">[Brand Name]</a>
    <nav>
      <a href="index.html">Home</a>
      <a href="shop.html">Shop</a>
      <a href="cart.html">Cart</a>
      <!-- Add links to ALL HTML pages listed in FILES -->
    </nav>
    <div class="header-right">
      <input type="text" id="search-input" placeholder="Search products..." class="search-input">
      <div class="cart-summary">
        <span id="cart-count">0</span> items - $<span id="cart-subtotal">0.00</span>
        <a href="cart.html" class="cart-link">View Cart</a>
      </div>
    </div>
  </div>
</header>

For information_site or web_app:
<header>
  <div class="header-container">
    <a href="index.html" class="logo">[Brand Name]</a>
    <nav>
      <a href="index.html">Home</a>
      <a href="matches.html">Matches</a>
      <a href="results.html">Results</a>
      <!-- Add links to ALL HTML pages listed in FILES (NO shop/cart/checkout unless required) -->
    </nav>
    <div class="header-right">
      <input type="text" id="search-input" placeholder="Search..." class="search-input">
      <!-- NO cart section -->
    </div>
  </div>
</header>

REQUIRED CSS:
- Modern, professional design with proper spacing and alignment
- Responsive: Stacks vertically on mobile, horizontal on desktop (use flexbox or grid)
- Header background: Light color (#f8f9fa or similar), with border-bottom for separation
- Logo: Bold, prominent, clickable
- Navigation links: Hover effects, proper spacing
- Search input: Visible, accessible, with proper padding
- Cart summary (ecommerce_site only): Right-aligned, visible, updates dynamically
- Use flexbox or CSS Grid for layout
- Clear visual hierarchy and separation between sections

REQUIRED JAVASCRIPT:
- Search input (#search-input): Live filtering as user types (debounced recommended, 300ms)
- Cart display (ecommerce_site only): Updates automatically when items added/removed via localStorage
- Cart count/subtotal (ecommerce_site only): Read from localStorage on page load and update immediately
- updateCartDisplay() function (ecommerce_site only): Must be called after every cart operation and on page load
- All pages must update header cart display on load (ecommerce_site only, read from localStorage)
"""

# Standard Footer Component Specification
FOOTER_SOP = """
=== FOOTER COMPONENT - STANDARD OPERATING PROCEDURE ===

CRITICAL: Footer MUST appear on EVERY HTML page with IDENTICAL structure.

REQUIRED STRUCTURE:
- Company/Store information
- Links to important pages (About, Contact, Privacy Policy, etc.)
- Navigation links to all main pages
- Copyright notice
- Optional: Social media links

REQUIRED HTML STRUCTURE (must be identical on ALL pages):
<footer>
  <div class="footer-content">
    <div class="footer-section">
      <h3>About [Store Name]</h3>
      <p>Your one-stop shop for quality products. We offer the best selection and customer service.</p>
    </div>
    <div class="footer-section">
      <h3>Quick Links</h3>
      <ul>
        <li><a href="index.html">Home</a></li>
        <li><a href="shop.html">Shop</a></li>
        <li><a href="cart.html">Cart</a></li>
        <!-- Add links to ALL HTML pages listed in FILES -->
      </ul>
    </div>
    <div class="footer-section">
      <h3>Contact</h3>
      <p>Email: info@store.com</p>
      <p>Phone: (123) 456-7890</p>
    </div>
  </div>
  <div class="footer-bottom">
    <p>&copy; 2025 [Store Name]. All rights reserved.</p>
  </div>
</footer>

REQUIRED CSS:
- Modern, clean design with dark background (#343a40 or similar) and light text (#ffffff)
- Responsive: Stacks vertically on mobile, multi-column (3 columns) on desktop (use flexbox or grid)
- Clear visual separation from main content (margin-top: 40px or similar)
- Footer content: Proper padding (20px or more), readable text
- Footer bottom: Centered text, border-top for separation
- Consistent styling with overall theme
- Links: Hover effects, proper spacing

REQUIRED JAVASCRIPT:
- None required (static content)
- Optional: Dynamic year in copyright (use new Date().getFullYear())
"""

# Standard Cart Component Specification
CART_SOP = """
=== CART COMPONENT - STANDARD OPERATING PROCEDURE ===

REQUIRED FUNCTIONALITY:
- Add to Cart: Button on product cards, stores in localStorage
- Remove from Cart: Button to remove items
- Update Quantity: Increase/decrease controls
- Calculate Totals: Subtotal, tax (if applicable), grand total
- Persist Data: Use localStorage key "cart" (JSON format)
- Display Updates: Update header cart count and subtotal in real-time

REQUIRED LOCALSTORAGE FORMAT:
{
  "items": [
    {
      "id": "product-1",
      "name": "Product Name",
      "price": 29.99,
      "quantity": 2,
      "image": "path/to/image.jpg"
    }
  ]
}

PRODUCT DATA SOURCE:
- CRITICAL: products.json is ALWAYS in SHARED_ASSETS. Products MUST be loaded from products.json file, NEVER hardcoded in HTML.
- Engineer MUST generate products.json file with all products from PRODUCTS section
- JavaScript MUST load products from products.json using fetch('products.json') on DOMContentLoaded
- JSON format (products.json): Array of product objects, each with id, name, price, category, description, image
  Example format:
  [
    {
      "id": 1,
      "name": "Product Name",
      "price": 29.99,
      "category": "Category Name",
      "description": "Product description text",
      "image": "https://via.placeholder.com/300x300?text=Product+Name"
    }
  ]
  OR wrapped format:
  {
    "products": [
      {"id": 1, "name": "...", "price": 29.99, "category": "...", "description": "...", "image": "..."}
    ],
    "total": 10
  }
- CRITICAL: If fetch fails (404, network error), JavaScript MUST have fallback: show error message or empty array. NEVER use hardcoded products array.
- CRITICAL: Product container ID in HTML must match ID used in JavaScript. STANDARD ID: Use id="products-container" (with 's', plural) consistently in both HTML and JavaScript. Example: HTML has <section id="products-container"></section>, JavaScript uses document.getElementById('products-container')

REQUIRED HTML STRUCTURE (Cart Page):
<div class="cart-container">
  <h1>Shopping Cart</h1>
  <div id="cart-items">
    <!-- Dynamically populated from localStorage -->
  </div>
  <div class="cart-summary">
    <p>Subtotal: <span id="cart-subtotal">$0.00</span></p>
    <p>Total: <span id="cart-total">$0.00</span></p>
    <button id="checkout-btn">Checkout</button>
  </div>
</div>

REQUIRED JAVASCRIPT FUNCTIONS:
- addToCart(productId, productName, price, image): Add/update item in cart
- removeFromCart(productId): Remove item from cart
- updateQuantity(productId, newQuantity): Update item quantity
- calculateTotals(): Calculate and display subtotal/total
- updateCartDisplay(): Update header cart count (#cart-count) and subtotal (#cart-subtotal) - MUST update these elements on ALL pages
- loadCartFromStorage(): Load cart from localStorage on page load
- saveCartToStorage(): Save cart to localStorage
- CRITICAL: updateCartDisplay() MUST be called after every cart operation (add, remove, update quantity) and on page load
- CRITICAL: Container IDs must match - if HTML has #cart-count and #cart-subtotal, JavaScript MUST use these exact IDs
"""

# Standard Filter Component Specification
FILTER_SOP = """
=== FILTER COMPONENT - STANDARD OPERATING PROCEDURE ===

REQUIRED FUNCTIONALITY:
- Category Filter: Dropdown or buttons to filter products by category
- "All" Option: Show all products when "All" selected
- Live Filtering: Products hide/show immediately when filter changes
- URL Parameters (optional): Update URL to reflect current filter

REQUIRED HTML STRUCTURE:
<div class="filter-container">
  <label for="category-filter">Filter by Category:</label>
  <select id="category-filter">
    <option value="all">All</option>
    <option value="category1">Category 1</option>
    <option value="category2">Category 2</option>
  </select>
</div>

OR (Button-based):
<div class="filter-buttons">
  <button class="filter-btn active" data-category="all">All</button>
  <button class="filter-btn" data-category="category1">Category 1</button>
  <button class="filter-btn" data-category="category2">Category 2</button>
</div>

REQUIRED JAVASCRIPT:
- CRITICAL: MUST attach event listener on filter element (select or buttons) - use addEventListener('change', ...) for select or addEventListener('click', ...) for buttons
- Filter function: Hide products that don't match selected category (use display: none or remove from DOM)
- Show all products when "all" selected
- Update active state on filter buttons (if using buttons)
- Products must have data-category attribute matching category names
- Implementation: Get the filter element using getElementById, check if it exists, then attach a change event listener that calls the filter function with the selected value

REQUIRED PRODUCT HTML:
<div class="product-card" data-category="category1">
  <!-- Product content -->
</div>
"""

# Standard Sort Component Specification
SORT_SOP = """
=== SORT COMPONENT - STANDARD OPERATING PROCEDURE ===

REQUIRED FUNCTIONALITY:
- Sort Options: Price (Low to High), Price (High to Low), Name (A to Z), Name (Z to A)
- Live Sorting: Products reorder immediately when sort option changes
- Preserve Filter: Sorting should work with active category filter

REQUIRED HTML STRUCTURE:
<div class="sort-container">
  <label for="sort-select">Sort by:</label>
  <select id="sort-select">
    <option value="price-asc">Price: Low to High</option>
    <option value="price-desc">Price: High to Low</option>
    <option value="name-asc">Name: A to Z</option>
    <option value="name-desc">Name: Z to A</option>
  </select>
</div>

REQUIRED JAVASCRIPT:
- CRITICAL: MUST attach event listener on sort select element - use addEventListener('change', ...) on the sort select element
- Sort function that:
  * Extracts all visible products (respecting current filter)
  * Sorts based on selected option:
    - price-asc: Sort by price (numeric, ascending)
    - price-desc: Sort by price (numeric, descending)
    - name-asc: Sort by product name (alphabetical, ascending)
    - name-desc: Sort by product name (alphabetical, descending)
  * Re-inserts sorted products into DOM
- Products must have data-price and product name accessible for sorting
- Implementation: Get the sort select element using getElementById, check if it exists, then attach a change event listener that calls the sort function with the selected value

REQUIRED PRODUCT HTML:
<div class="product-card" data-price="29.99">
  <h3 class="product-name">Product Name</h3>
  <!-- Other product content -->
</div>
"""

# Standard Search Component Specification
SEARCH_SOP = """
=== SEARCH COMPONENT - STANDARD OPERATING PROCEDURE ===

REQUIRED FUNCTIONALITY:
- Live Search: Filter products as user types (debounced for performance)
- Search by Name: Match product names (case-insensitive, partial match)
- Clear Search: Show all products when search field is empty
- Combine with Filter: Search should work with active category filter

REQUIRED HTML STRUCTURE:
<input type="text" id="search-input" placeholder="Search products...">

REQUIRED JAVASCRIPT:
- CRITICAL: MUST attach event listener on search input (#search-input) - use addEventListener('input', ...) or addEventListener('keyup', ...) for live search
- Debounce function (recommended: 300ms delay) to avoid excessive filtering while typing
- Search function that:
  * Gets search query (trimmed, lowercased)
  * If empty: Show all products (respecting category filter)
  * If not empty: Hide products whose name doesn't match query
  * Case-insensitive matching
  * Partial matching (contains, not exact match)
- Products must have searchable text (product name) accessible
- Implementation: Get the search input element using getElementById, check if it exists, then attach an input or keyup event listener that calls the search function with the input value

REQUIRED PRODUCT HTML:
<div class="product-card">
  <h3 class="product-name">Searchable Product Name</h3>
  <!-- Other product content -->
</div>
"""

# Combined Component Integration Guide
COMPONENT_INTEGRATION_SOP = """
=== COMPONENT INTEGRATION - STANDARD OPERATING PROCEDURE ===

WEBSITE_TYPE-SPECIFIC INTEGRATION:

For ecommerce_site:
1. Header: MUST appear on ALL HTML pages with IDENTICAL structure and exact same IDs (#search-input, #cart-count, #cart-subtotal)
2. Footer: MUST appear on ALL HTML pages with IDENTICAL structure
3. Cart: Header cart display + dedicated cart page
4. Checkout: Dedicated checkout.html consumes cart/localStorage totals, reuses header/footer, and surfaces forms for shipping/payment
5. Filter: Appears on shop/product listing pages
6. Sort: Appears on shop/product listing pages (alongside filter)
7. Search: Integrated into header, works on all pages

REQUIRED SHARED ASSETS (ecommerce_site):
- styles.css: Contains all component styles (header, footer, products, cart, etc.)
- script.js: Contains all component JavaScript (cart, filter, sort, search, product loading)
- products.json: CRITICAL - MUST be generated with all products
- All HTML pages must link both files:
  <link rel="stylesheet" href="styles.css">
  <script src="script.js"></script>

For information_site or web_app:
1. Header: MUST appear on ALL HTML pages with IDENTICAL structure and exact same IDs (#search-input) - NO cart-count or cart-subtotal
2. Footer: MUST appear on ALL HTML pages with IDENTICAL structure
3. NO Cart/Checkout: Do NOT include cart.html, checkout.html, or cart functionality unless explicitly required
4. Filter: Appears on content listing pages (e.g., matches, results) if needed
5. Sort: Appears on content listing pages (alongside filter) if needed
6. Search: Integrated into header, works on all pages

REQUIRED SHARED ASSETS (information_site/web_app):
- styles.css: Contains all component styles (header, footer, content cards, etc.)
- script.js: Contains all component JavaScript (filter, sort, search, content loading)
- Domain-specific JSON files (e.g., matches.json, results.json) if JavaScript fetches them
- All HTML pages must link both files:
  <link rel="stylesheet" href="styles.css">
  <script src="script.js"></script>

REQUIRED DATA FLOW:
1. Products: 
   - CRITICAL: products.json is ALWAYS in SHARED_ASSETS. Products MUST be loaded from JSON, NEVER hardcoded in HTML.
   - Engineer MUST generate products.json file with all products from PRODUCTS section
   - HTML must have empty product container id="products-container" (e.g., <section id="products-container"></section>)
   - JavaScript MUST load products.json using fetch('products.json') on DOMContentLoaded
   - JavaScript MUST generate product cards dynamically and insert into #products-container
   - JavaScript MUST handle fetch errors with fallback (error message or empty array). NEVER use hardcoded products array.
   - products.json format: Array of objects with id, name, price, category, description, image
2. Cart: Stored in localStorage (key: "cart"), updates header display on all pages
3. Filter State: Managed in JavaScript (can optionally use URL params)
4. Sort State: Managed in JavaScript (can optionally use URL params)
5. Search State: Managed in JavaScript (cleared on page navigation)

REQUIRED CONSISTENCY:
- ALL pages use IDENTICAL header structure with exact same IDs
- ALL pages use IDENTICAL footer structure
- ALL pages link same CSS and JS files from SHARED_ASSETS
- Product cards have consistent structure and data attributes
- Cart operations work consistently across all pages
- JavaScript detects current page and initializes appropriate functionality
- All event listeners check if elements exist before attaching (use optional chaining or if statements)
"""


CHECKOUT_SOP = """
=== CHECKOUT PAGE - STANDARD OPERATING PROCEDURE ===

PURPOSE:
- Provide a dedicated checkout.html page that summarizes the cart, gathers shipping/billing information, lets users select payment/shipping methods, and confirms the order.

REQUIRED STRUCTURE:
- Shared header/footer identical to other pages (links to index.html, shop.html, cart.html, checkout.html, #search-input, #cart-count, #cart-subtotal).
- Order summary section with container IDs (#checkout-summary, #checkout-subtotal, #checkout-total) so JavaScript can inject cart totals from localStorage.
- Customer information form (e.g., <form id="checkout-form">) with inputs for name, email, phone, shipping address (street, city, state, ZIP), and optional billing info.
- Payment section with selectable options (radio buttons) for card, PayPal, etc., plus inputs for card number/expiry/CVV when applicable.
- Shipping method select or radio group (standard vs express) with price indicators.
- Terms acknowledgement checkbox and a primary CTA button (id="place-order-button") to submit the checkout form.

ACCESSIBILITY & UX:
- Use semantic sections (<section>, <form>, <fieldset>) with aria-labelledby labels.
- Inputs must have associated <label> elements; group related controls with fieldsets/legends.
- Provide inline validation/error containers (e.g., <p class="form-error" role="alert">) that JS can toggle.

JAVASCRIPT HOOKS:
- Expect script.js to read cart data from localStorage, populate #checkout-summary and totals, validate forms, and handle submission (even if final implementation is stubbed).
- Ensure IDs/classes referenced above exist exactly so JS can query them.
"""


def get_all_sops() -> dict[str, str]:
    """Get all SOP templates as a dictionary."""
    return {
        "website_type": WEBSITE_TYPE_SOP,
        "header": HEADER_SOP,
        "footer": FOOTER_SOP,
        "cart": CART_SOP,
        "filter": FILTER_SOP,
        "sort": SORT_SOP,
        "search": SEARCH_SOP,
        "checkout": CHECKOUT_SOP,
        "integration": COMPONENT_INTEGRATION_SOP,
    }


def get_sop_summary(website_type: str = "") -> str:
    """Get a concise summary of all SOPs for inclusion in agent briefs.
    
    Args:
        website_type: One of "information_site", "ecommerce_site", "web_app". 
                      If empty, returns generic summary with conditional guidance.
    """
    website_type = website_type.lower() if website_type else ""
    is_ecommerce = website_type == "ecommerce_site"
    is_information = website_type == "information_site"
    
    base_summary = """
=== DEFAULT COMPONENT BEHAVIORS (SOP) ===

The following components and patterns have standardized implementations. DO NOT guess or invent:
- Use these exact specifications to ensure consistency.

0. WEBSITE_TYPE: Always classify the requested site before choosing structures/SOPs
   - WEBSITE_TYPE must be one of: information_site, ecommerce_site, web_app
   - Default to information_site for content/schedule/results/news style sites
   - Use ecommerce_site ONLY when requirements mention selling/buying/cart/checkout/payment/orders/tickets
   - For information_site and web_app, DO NOT introduce cart/checkout/products.json unless explicitly requested

1. HEADER: MUST appear on EVERY HTML page with IDENTICAL structure
   - Logo (left, clickable, links to homepage)
   - Navigation menu (center, links to ALL pages listed in FILES - NOT hardcoded shop/cart/checkout unless they exist in FILES)
   - Search bar (#search-input on input element itself) for searching content/products
"""
    
    if is_ecommerce:
        base_summary += """   - Cart summary (right, shows item count + subtotal) with IDs #cart-count, #cart-subtotal
   - Navigation MUST include links to shop.html, cart.html, checkout.html (if they exist in FILES)
"""
    elif is_information:
        base_summary += """   - NO cart summary (#cart-count, #cart-subtotal) unless requirements explicitly mention cart/checkout
   - Navigation should include domain-appropriate links (e.g., index.html, matches.html, results.html, about.html)
   - DO NOT add shop.html, cart.html, checkout.html links unless they exist in FILES
"""
    else:
        base_summary += """   - For ecommerce_site: include cart summary (right, shows item count + subtotal) with IDs #cart-count, #cart-subtotal
   - For information_site / web_app: ONLY include cart summary if requirements explicitly mention cart/checkout
"""
    
    base_summary += """   - Modern, professional design with proper spacing

2. FOOTER: MUST appear on EVERY HTML page with IDENTICAL structure
   - Company info + Navigation links + Contact + Copyright
   - Navigation links should match pages listed in FILES (NOT hardcoded shop/cart/checkout)
   - Responsive multi-column layout (3 columns desktop, stacked mobile)
   - Dark background, light text, professional design
"""
    
    if is_ecommerce:
        base_summary += """
3. CART: localStorage-based with add/remove/update quantity
   - localStorage key: "cart"
   - Updates header cart display (#cart-count, #cart-subtotal) automatically on ALL pages
   - updateCartDisplay() must be called after every cart operation and on page load

4. PRODUCTS:
   - CRITICAL: products.json is ALWAYS in SHARED_ASSETS. Engineer MUST generate products.json file, HTML has empty container id="products-container", JavaScript loads from JSON
   - Products MUST NEVER be hardcoded in HTML
   - products.json format: Array of objects with id, name, price, category, description, image
   - JavaScript MUST handle fetch errors with fallback (error message or empty array). NEVER use hardcoded products array.

5. FILTER: Category dropdown/buttons
   - Products have data-category attribute
   - "All" option shows everything
   - Must attach event listeners on filter elements

6. SORT: Price/Name, Ascending/Descending
   - Products have data-price attribute
   - Works with active filter
   - Must attach event listeners on sort elements

7. SEARCH: Live search in header (#search-input)
   - Searches product names (case-insensitive, partial match)
   - Works with active filter
   - Debounced (300ms recommended)
   - Must attach event listeners on search input

8. CHECKOUT: Dedicated checkout.html page
   - Shared header/footer with nav links to index/shop/cart/checkout
   - Order summary containers (#checkout-summary, #checkout-subtotal, #checkout-total) fed by cart/localStorage
   - Checkout form (#checkout-form) capturing contact, shipping, billing, payment method, agreement checkbox, and Place Order button
   - Hooks for JavaScript validation/submission (ids must match exactly)
"""
    elif is_information:
        base_summary += """
3. CONTENT DATA: Load from domain-specific JSON files (e.g., matches.json, results.json)
   - JSON files should be listed in SHARED_ASSETS if JavaScript fetches them
   - Container IDs must match JavaScript selectors (e.g., id="matches-container" if JS uses getElementById('matches-container'))
   - Use domain-appropriate class names (e.g., MatchManager, ResultsManager) - NOT ProductManager/CartManager
   - JavaScript MUST handle fetch errors with fallback (error message or empty array)

4. FILTER/SORT/SEARCH: For content entities (matches, results, articles, etc.)
   - Filter by domain attributes (e.g., league, date, category)
   - Sort by domain attributes (e.g., date, name, league)
   - Search in header (#search-input) searches content names/descriptions
   - Debounced (300ms recommended)
   - Must attach event listeners on filter/sort/search elements
"""
    else:
        base_summary += """
3. CART: (ONLY for ecommerce_site) localStorage-based with add/remove/update quantity
   - localStorage key: "cart"
   - Updates header cart display (#cart-count, #cart-subtotal) automatically on ALL pages
   - updateCartDisplay() must be called after every cart operation and on page load

4. PRODUCTS/CONTENT DATA: 
   - For ecommerce_site: products.json in SHARED_ASSETS, container id="products-container"
   - For information_site: domain-specific JSON files (matches.json, results.json, etc.), domain-specific container IDs
   - Data MUST NEVER be hardcoded in HTML
   - JavaScript MUST handle fetch errors with fallback

5-7. FILTER/SORT/SEARCH: Works with products (ecommerce) or content entities (information_site)
   - Filter/Sort by domain attributes
   - Search in header (#search-input)
   - Debounced (300ms recommended)
"""
    
    base_summary += """
9. INTEGRATION: ALL pages share IDENTICAL header/footer/CSS/JS
   - Header structure identical across all pages (but navigation links match FILES, not hardcoded)
   - Footer structure identical across all pages
   - All pages link same CSS and JS files (consistent paths: either all 'styles.css' or all 'SHARED_ASSETS/styles.css')
   - JavaScript detects current page and initializes appropriate functionality
   - All event listeners check if elements exist before attaching

For detailed specifications, refer to the full SOP templates.
"""
    return base_summary

# Reusable HTML snippets for header/footer/nav scaffolding
HEADER_HTML_SNIPPET = """
<!-- HEADER_SNIPPET: Copy to EVERY HTML page, then replace [BRAND_NAME] and duplicate nav links for ALL pages -->
<header class="site-header">
  <div class="header-container">
    <a href="index.html" class="logo">[BRAND_NAME]</a>
    <nav class="primary-nav">
      <!-- Replace the examples with links to EVERY HTML page listed in FILES -->
      <a href="index.html">Home</a>
      <a href="shop.html">Shop</a>
      <a href="cart.html">Cart</a>
    </nav>
    <div class="header-actions">
      <input type="text" id="search-input" placeholder="Search products..." />
      <div class="cart-summary">
        <span id="cart-count">0</span> items · $<span id="cart-subtotal">0.00</span>
        <a href="cart.html" class="cart-link">View Cart</a>
      </div>
    </div>
  </div>
</header>
"""

FOOTER_HTML_SNIPPET = """
<!-- FOOTER_SNIPPET: Copy to EVERY HTML page and adjust text/links as needed -->
<footer class="site-footer">
  <div class="footer-content">
    <section>
      <h3>About [BRAND_NAME]</h3>
      <p>Your one-stop shop for curated fashion essentials. Quality service, fast shipping.</p>
    </section>
    <section>
      <h3>Quick Links</h3>
      <ul>
        <!-- Include links to EVERY HTML page listed in FILES -->
        <li><a href="index.html">Home</a></li>
        <li><a href="shop.html">Shop</a></li>
        <li><a href="cart.html">Cart</a></li>
      </ul>
    </section>
    <section>
      <h3>Contact</h3>
      <p>Email: info@example.com</p>
      <p>Phone: (123) 456-7890</p>
    </section>
  </div>
  <div class="footer-bottom">
    <p>&copy; 2025 [BRAND_NAME]. All rights reserved.</p>
  </div>
</footer>
"""

NAV_LINKS_GUIDE = """
- Duplicate the <a> items in the header nav and footer quick links so that EVERY HTML file listed in FILES has a link.
- For example, if FILES includes about.html or contact.html, add <a href="about.html">About</a>, etc.
- Keep link text concise (Home, Shop, Cart, About, Contact, etc.) and consistent across every page.
"""


def get_component_snippets_text(website_type: str = "") -> str:
    """Return ready-to-use component snippets for prompts.
    
    Args:
        website_type: One of "information_site", "ecommerce_site", "web_app".
                      If empty, returns generic snippets with conditional guidance.
    """
    website_type = website_type.lower() if website_type else ""
    is_ecommerce = website_type == "ecommerce_site"
    
    if is_ecommerce:
        header_snippet = HEADER_HTML_SNIPPET
        nav_guidance = NAV_LINKS_GUIDE
    else:
        # Information site version - no cart UI
        header_snippet = """
<!-- HEADER_SNIPPET: Copy to EVERY HTML page, then replace [BRAND_NAME] and duplicate nav links for ALL pages -->
<header class="header">
  <div class="header__container">
    <a href="index.html" class="header__logo">[BRAND_NAME]</a>
    <nav class="header__nav">
      <!-- Replace the examples with links to EVERY HTML page listed in FILES -->
      <a href="index.html">Home</a>
      <a href="matches.html">Matches</a>
      <a href="results.html">Results</a>
      <a href="about.html">About</a>
    </nav>
    <div class="header__search">
      <input type="text" id="search-input" placeholder="Search..." class="header__search-input" />
    </div>
  </div>
</header>
"""
        nav_guidance = """
- Duplicate the <a> items in the header nav and footer quick links so that EVERY HTML file listed in FILES has a link.
- Use domain-appropriate link text (e.g., Home, Matches, Results, About) - NOT shop/cart/checkout unless they exist in FILES.
- Keep link text concise and consistent across every page.
"""
    
    return f"""
=== REQUIRED COMPONENT SNIPPETS ===
Copy these skeletons into EVERY HTML page. Replace [BRAND_NAME] and duplicate nav links so they cover ALL HTML files listed in FILES.{" Do NOT change IDs (#search-input, #cart-count, #cart-subtotal)." if is_ecommerce else " Do NOT change ID (#search-input)."}

--- HEADER SNIPPET ---
{header_snippet.strip()}

--- FOOTER SNIPPET ---
{FOOTER_HTML_SNIPPET.strip()}

--- NAVIGATION GUIDANCE ---
{nav_guidance.strip()}
"""

