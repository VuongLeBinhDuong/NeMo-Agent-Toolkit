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

# Standard Header Component Specification
HEADER_SOP = """
=== HEADER COMPONENT - STANDARD OPERATING PROCEDURE ===

CRITICAL: Header MUST appear on EVERY HTML page with IDENTICAL structure and IDs.

REQUIRED STRUCTURE:
- Logo/Brand Name: Left-aligned, clickable (links to homepage/index.html)
- Navigation Menu: Horizontal links to ALL pages listed in FILES (e.g., Home, Shop, Cart, etc.)
- Search Bar: Input field with id="search-input" (MUST be on the input element itself, not a wrapper div), placeholder="Search products..."
- Cart Section: Right-aligned, showing:
  * Item count: <span id="cart-count">0</span> items
  * Subtotal: $<span id="cart-subtotal">0.00</span>
  * Optional: Clickable to navigate to cart page

REQUIRED HTML STRUCTURE (must be identical on ALL pages):
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

REQUIRED CSS:
- Modern, professional design with proper spacing and alignment
- Responsive: Stacks vertically on mobile, horizontal on desktop (use flexbox or grid)
- Header background: Light color (#f8f9fa or similar), with border-bottom for separation
- Logo: Bold, prominent, clickable
- Navigation links: Hover effects, proper spacing
- Search input: Visible, accessible, with proper padding
- Cart summary: Right-aligned, visible, updates dynamically
- Use flexbox or CSS Grid for layout
- Clear visual hierarchy and separation between sections

REQUIRED JAVASCRIPT:
- Search input (#search-input): Live filtering as user types (debounced recommended, 300ms)
- Cart display: Updates automatically when items added/removed via localStorage
- Cart count/subtotal (#cart-count, #cart-subtotal): Read from localStorage on page load and update immediately
- updateCartDisplay() function: Must be called after every cart operation and on page load
- All pages must update header cart display on load (read from localStorage)
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
- Products can be hardcoded in HTML (default) OR loaded from products.json file
- If "products.json" is listed in SHARED_ASSETS: MUST load from products.json using fetch() on page initialization
- If products.json is NOT in SHARED_ASSETS: Products MUST be hardcoded directly in HTML markup
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
- CRITICAL: If products.json is in SHARED_ASSETS, engineer MUST generate products.json file with all products from PRODUCTS section
- CRITICAL: If products.json exists, JavaScript MUST load it using fetch('products.json') on DOMContentLoaded
- CRITICAL: If fetch fails (404, network error), JavaScript MUST have fallback: either use hardcoded products array or show error message. Do NOT leave page empty.
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

REQUIRED INTEGRATION:
1. Header: MUST appear on ALL HTML pages with IDENTICAL structure and exact same IDs (#search-input, #cart-count, #cart-subtotal)
2. Footer: MUST appear on ALL HTML pages with IDENTICAL structure
3. Cart: Header cart display + dedicated cart page
4. Filter: Appears on shop/product listing pages
5. Sort: Appears on shop/product listing pages (alongside filter)
6. Search: Integrated into header, works on all pages

REQUIRED SHARED ASSETS:
- styles.css: Contains all component styles (header, footer, products, cart, etc.)
- script.js: Contains all component JavaScript (cart, filter, sort, search, product loading)
- products.json (optional): If listed in SHARED_ASSETS, MUST be generated with all products
- All HTML pages must link both files:
  <link rel="stylesheet" href="styles.css">
  <script src="script.js"></script>

REQUIRED DATA FLOW:
1. Products: 
   - If "products.json" is in SHARED_ASSETS: 
     * Engineer MUST generate products.json file with all products from PRODUCTS section
     * HTML must have empty product container (e.g., <section id="product-list"></section>)
     * JavaScript MUST load products.json using fetch('products.json') on DOMContentLoaded
     * JavaScript MUST generate product cards dynamically and insert into container
     * JavaScript MUST handle fetch errors with fallback (hardcoded products or error message)
   - If products.json is NOT in SHARED_ASSETS:
     * Products MUST be hardcoded directly in HTML markup with data attributes (data-category, data-price)
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


def get_all_sops() -> dict[str, str]:
    """Get all SOP templates as a dictionary."""
    return {
        "header": HEADER_SOP,
        "footer": FOOTER_SOP,
        "cart": CART_SOP,
        "filter": FILTER_SOP,
        "sort": SORT_SOP,
        "search": SEARCH_SOP,
        "integration": COMPONENT_INTEGRATION_SOP,
    }


def get_sop_summary() -> str:
    """Get a concise summary of all SOPs for inclusion in agent briefs."""
    return """
=== DEFAULT COMPONENT BEHAVIORS (SOP) ===

The following components have standardized implementations. DO NOT guess or invent:
- Use these exact specifications to ensure consistency.

1. HEADER: MUST appear on EVERY HTML page with IDENTICAL structure
   - Logo (left, clickable, links to homepage)
   - Navigation menu (center, links to ALL pages)
   - Search bar (#search-input on input element itself)
   - Cart summary (right, shows item count + subtotal)
   - Required IDs: #search-input, #cart-count, #cart-subtotal
   - Modern, professional design with proper spacing

2. FOOTER: MUST appear on EVERY HTML page with IDENTICAL structure
   - Company info + Navigation links + Contact + Copyright
   - Responsive multi-column layout (3 columns desktop, stacked mobile)
   - Dark background, light text, professional design

3. CART: localStorage-based with add/remove/update quantity
   - localStorage key: "cart"
   - Updates header cart display (#cart-count, #cart-subtotal) automatically on ALL pages
   - updateCartDisplay() must be called after every cart operation and on page load

4. PRODUCTS:
   - If "products.json" is in SHARED_ASSETS: Engineer MUST generate products.json file, HTML has empty container, JavaScript loads from JSON
   - If products.json NOT in SHARED_ASSETS: Products hardcoded in HTML with data attributes
   - products.json format: Array of objects with id, name, price, category, description, image
   - JavaScript MUST handle fetch errors with fallback (hardcoded products or error message)

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

8. INTEGRATION: ALL pages share IDENTICAL header/footer/CSS/JS
   - Header structure identical across all pages
   - Footer structure identical across all pages
   - All pages link same CSS and JS files from SHARED_ASSETS
   - JavaScript detects current page and initializes appropriate functionality
   - All event listeners check if elements exist before attaching

For detailed specifications, refer to the full SOP templates.
"""

