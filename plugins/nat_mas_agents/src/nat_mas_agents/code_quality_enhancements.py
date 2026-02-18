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

"""Code quality enhancements for MAS engineer phase.

This module provides utilities to improve code generation quality by:
- Building enhanced queries with quality guidelines
- Providing code examples and reference implementations
- Adding code refinement capabilities
"""

HTML_QUALITY_GUIDELINES = """
QUALITY REQUIREMENTS FOR HTML:
- Use semantic HTML5 elements (<header>, <nav>, <main>, <section>, <article>, <footer>, <aside>, <figure>, <figcaption>)
- Include comprehensive accessibility attributes (aria-labels, aria-live, aria-expanded, aria-hidden, roles, tabindex)
- Ensure responsive design with a mobile-first approach
- Use meaningful class names following BEM methodology (block__element--modifier) that match the canonical shared component class names (header, header__*, header__nav, header__search-input, header__cart, footer__*, products, products__*, product-card__*, etc.).
- Do NOT use <style> tags or inline style="..." attributes; all visual styling must live in external stylesheets (for example, styles.css) linked via <link rel="stylesheet" href="styles.css"> in the <head>.
- Include comprehensive meta tags for SEO (title, description, viewport, Open Graph, Twitter Cards, canonical URLs)
- Add Schema.org microdata or JSON-LD structured data for products, organization, breadcrumbs
- Validate HTML structure and ensure proper nesting
- Ensure all interactive elements are keyboard accessible (focus states, keyboard navigation)
- Use lazy loading for images (loading="lazy") and responsive images (srcset, sizes)
- Include proper form labels, error message containers, and validation feedback
- Ensure proper heading hierarchy (h1 → h2 → h3) with only one h1 per page
- Add loading states and skeleton screens for dynamic content
- Include modal dialogs with proper ARIA attributes (role="dialog", aria-modal="true")
- Add tooltips and dropdown menus with proper accessibility
- Use data attributes for JavaScript hooks (data-* attributes)
- Include language and direction attributes on the <html> element (e.g., lang="en", dir="ltr" or "rtl")
- Avoid hardcoded copy that contradicts PRODUCT, CATEGORIES, or SORT_OPTIONS from the structured handoff.
"""

CSS_QUALITY_GUIDELINES = """
QUALITY REQUIREMENTS FOR CSS:

CRITICAL: Use ONLY pure CSS - NO SCSS/SASS functions or syntax!
- DO NOT use: darken(), lighten(), @mixin, @include, @import (SCSS syntax)
- DO NOT use: SCSS variables ($variable), nesting, or other SCSS features
- Use ONLY standard CSS: CSS custom properties (var(--variable)), standard functions, etc.
- For color darkening/lightening, use one of these pure CSS approaches:
  * CSS color-mix(): color-mix(in srgb, var(--accent-color) 90%, black 10%)
  * HSL manipulation: hsl(hue, saturation%, lightness%)
  * Hardcode calculated colors: If accent is #007bff, darker version is #0066cc
  * Use opacity/transparency: rgba() or opacity property

- Use CSS custom properties (CSS variables) for theming, colors, spacing, typography, and animations
- Implement comprehensive responsive breakpoints (mobile: <576px, tablet: 576-992px, desktop: 992-1440px, large: >1440px)
- Use modern CSS features (Grid, Flexbox, CSS animations, keyframes, :is, :where, :has, :focus-visible, :focus-within)
- Follow mobile-first responsive design approach with progressive enhancement
- Use meaningful class names following BEM methodology (block__element--modifier)
- Organize CSS with clear sections (reset/normalize, CSS variables, base styles, components, utilities, animations)
- Ensure cross-browser compatibility with vendor prefixes where needed
- Use efficient selectors (avoid deep nesting > 3 levels, prefer class selectors)
- Include smooth transitions, hover effects, focus states, and active states for better UX
- Use relative units (rem, em, %, vw, vh) instead of fixed pixels where appropriate
- Implement comprehensive spacing scale (0.25rem, 0.5rem, 0.75rem, 1rem, 1.5rem, 2rem, 3rem, 4rem)
- Implement typography system with font-size scale, line-height, font-weight, and letter-spacing
- Use transform/opacity for animations (better performance than position/width/height changes)
- Implement CSS animations with @keyframes for complex animations (fade-in, slide-in, bounce, pulse)
- Use CSS Grid advanced features (auto-fit, auto-fill, minmax, subgrid where supported)
- Implement dark mode support using prefers-color-scheme or data-theme attribute
- Use gradients (linear-gradient, radial-gradient) for backgrounds and overlays
- Use backdrop-filter for glassmorphism effects (blur, brightness)
- Implement container queries where appropriate (for component-level responsiveness)
- Add smooth scrolling behavior (scroll-behavior: smooth)
- Use CSS filters (blur, brightness, contrast, grayscale) for image effects
- PRODUCT GRID: Use CSS Grid for #products-container with responsive columns (1 mobile, 2 tablet, 3 desktop, 4 large)
- PRODUCT CARDS: Create beautiful, modern card design with:
  * Flexbox layout for card content (flex-direction: column)
  * Image wrapper with aspect ratio (padding-top technique or aspect-ratio property)
  * Advanced hover effects (transform: translateY, scale, box-shadow transitions, image zoom)
  * Loading states with skeleton screens or shimmer effects
  * Proper spacing and padding (use rem units from spacing scale)
  * Card footer with price and button aligned horizontally
  * Smooth transitions for all interactive elements (0.2s-0.3s ease)
  * Box shadows for depth (subtle on default, stronger on hover, multiple shadow layers)
  * Rounded corners (border-radius: 0.5rem or similar, can vary by element)
  * Image object-fit: cover for consistent image display
  * Overlay effects on hover (darken, gradient overlay)
  * Badge/ribbon support for sale items or featured products
- MODAL/DIALOG: Implement modal dialogs with backdrop, animation, and proper z-index layering
- TOOLTIPS: Create tooltips with CSS-only or JavaScript-enhanced versions
- DROPDOWN MENUS: Implement dropdown menus with smooth animations and proper positioning
- LOADING STATES: Add skeleton screens, spinners, or progress indicators
- ANIMATIONS: Use @keyframes for entrance animations, loading states, and micro-interactions
- Establish global design tokens (colors, typography, spacing, radii, shadows, animation durations) and reuse them across every component.
- Style base layout primitives (body, main, sections, containers, utility classes) with fluid spacing via clamp() and container queries for a cohesive aesthetic.
- Provide polished treatments for header/nav, hero banners, filter/sort/search toolbars, product grids/cards, cart tables, checkout forms, modals/toasts, alert banners, and utility badges.
- Layer gradients, texture overlays, and tasteful glassmorphism/backdrop-filter effects to avoid flat surfaces while keeping contrast accessible.
- Implement explicit :focus-visible, :focus-within, hover, active, disabled, and [aria-*] state styles so interactive elements feel intentional.
- Respect motion accessibility: pair animations with @media (prefers-reduced-motion: reduce) fallbacks while still delivering delightful micro-interactions elsewhere.
- Define reusable @keyframes (shimmer, fade, slide) and surface-level utilities (e.g., .pill, .tag, .surface) so engineers can express state without rewriting CSS.
"""

JAVASCRIPT_QUALITY_GUIDELINES = """
QUALITY REQUIREMENTS FOR JAVASCRIPT:
- Use modern ES6+ features (arrow functions, const/let, template literals, destructuring, async/await, spread operator, rest parameters)
- Use ES6+ classes for object-oriented code organization (ProductManager, CartManager, Modal, etc.)
- Implement proper error handling with try-catch blocks and error boundaries
- Use async/await for asynchronous operations (avoid callback hell, prefer Promises)
- Follow functional programming principles where applicable (pure functions, immutability, higher-order functions)
- Add comprehensive JSDoc comments for classes, methods, and complex functions
- Use meaningful variable and function names (camelCase for variables/functions, PascalCase for classes, UPPER_CASE for constants)
- Implement proper event delegation for dynamic content (use event.target.closest() for delegation)
- Use debouncing/throttling for performance-critical operations (search, scroll, resize, window events)
- Avoid global variables, use module pattern, IIFE, or ES6 modules
- Organize code into logical modules/classes with single responsibility principle
- Ensure code is maintainable, well-structured, and follows SOLID principles
- Add proper error logging with console.error, console.warn (not console.log for errors)
- Validate inputs before processing (type checking, null/undefined checks, range validation)
- Use optional chaining (?.) and nullish coalescing (??) for safer code
- Implement graceful degradation for older browsers (feature detection, polyfills where needed)
- ALWAYS check if DOM elements exist before using: const el = document.getElementById('id'); if (el) { /* use */ }
- Use Intersection Observer API for lazy loading images and infinite scroll
- Implement state management patterns (simple state objects, event emitters, or observer pattern)
- Use Web APIs effectively (localStorage, sessionStorage, Fetch API, History API)
- Implement performance optimizations (virtual scrolling for large lists, requestAnimationFrame for animations)
- Add loading states and error states for async operations
- Implement modal/dialog management with proper focus trapping and keyboard navigation
- Use data attributes for JavaScript hooks (data-* attributes) instead of classes
- Implement proper cleanup (remove event listeners, clear timeouts/intervals, abort fetch requests)
- Use Map/Set for better performance with large datasets
- Implement proper form validation with real-time feedback
- Add keyboard navigation support (Enter, Escape, Arrow keys, Tab navigation)
- Use requestAnimationFrame for smooth animations and scroll effects
- Implement proper URL state management (update URL params for filters/sort without page reload)
- Add analytics tracking hooks (if applicable)
- Use Web Workers for heavy computations (if needed)
- Implement proper memory management (avoid memory leaks, clean up references)
"""


def get_quality_guidelines(file_type: str) -> str:
    """Get quality guidelines for a specific file type."""
    guidelines_map = {
        "html": HTML_QUALITY_GUIDELINES,
        "htm": HTML_QUALITY_GUIDELINES,
        "css": CSS_QUALITY_GUIDELINES,
        "js": JAVASCRIPT_QUALITY_GUIDELINES,
        "javascript": JAVASCRIPT_QUALITY_GUIDELINES,
    }
    
    file_type_lower = file_type.lower()
    # Remove extension if present
    if "." in file_type_lower:
        file_type_lower = file_type_lower.split(".")[-1]
    
    return guidelines_map.get(file_type_lower, "")


def build_enhanced_code_generation_query(
    filename: str,
    project_name: str,
    constraints: str,
    file_type: str,
    related_files: list[str] | None = None,
    code_examples: str | None = None,
) -> str:
    """Build enhanced query for code generation with quality guidelines.
    
    Args:
        filename: Name of the file to generate
        project_name: Name of the project
        constraints: Requirements and constraints from project manager
        file_type: Type of file (html, css, js, etc.)
        related_files: List of related files for context
        code_examples: Example code snippets to follow
        
    Returns:
        Enhanced query string with quality guidelines
    """
    quality_guidelines = get_quality_guidelines(file_type)
    critical_notes = _get_critical_notes(filename, file_type)
    
    query_parts = [
        f"Generate production-ready {file_type.upper()} code for '{filename}' in project '{project_name}'.",
        "",
        "=== REQUIREMENTS ===",
        constraints,
        "",
    ]
    
    if quality_guidelines:
        query_parts.extend([
            "=== CODE QUALITY STANDARDS ===",
            quality_guidelines,
            "",
        ])

    if critical_notes:
        query_parts.extend([
            "=== CRITICAL IMPLEMENTATION NOTES ===",
            *critical_notes,
            "",
        ])
    
    if related_files:
        query_parts.extend([
            "=== RELATED FILES (for consistency) ===",
            "Ensure code integrates seamlessly with:",
            ", ".join(related_files),
            "",
        ])
    
    if code_examples:
        query_parts.extend([
            "=== REFERENCE EXAMPLES ===",
            "Follow similar patterns from these examples:",
            code_examples,
            "",
        ])
    
    query_parts.extend([
        "=== OUTPUT REQUIREMENTS ===",
        "- Generate COMPLETE, WORKING code (no TODOs, no placeholders, no '...')",
        "- Follow modern best practices and coding standards",
        "- Ensure code is production-ready and maintainable",
        "- Include proper error handling and edge cases",
        "- Add helpful comments for complex logic",
        "- Ensure code integrates seamlessly with related files",
        "- Use semantic, accessible, and performant code",
        "- Follow the quality standards listed above",
    ])
    
    return "\n".join(query_parts)


# Code examples for reference
HEADER_EXAMPLE = """
<!-- Example: Modern, accessible header using canonical BEM classes and shared assets -->
<header class="header" role="banner">
  <div class="header__container">
    <a href="index.html" class="header__logo" aria-label="Fashion Marketplace Home">
      <img src="images/logo.png" alt="Fashion Marketplace Logo" width="150" height="50">
    </a>
    <nav class="header__nav" role="navigation" aria-label="Main navigation">
      <ul class="header__nav-list">
        <li class="header__nav-item"><a href="index.html" class="header__nav-link">Home</a></li>
        <li class="header__nav-item"><a href="shop.html" class="header__nav-link">Shop</a></li>
        <li class="header__nav-item"><a href="cart.html" class="header__nav-link">Cart</a></li>
        <li class="header__nav-item"><a href="checkout.html" class="header__nav-link">Checkout</a></li>
        <li class="header__nav-item"><a href="about.html" class="header__nav-link">About</a></li>
      </ul>
    </nav>
    <div class="header__search">
      <input 
        type="search" 
        id="search-input" 
        class="header__search-input"
        placeholder="Search products..." 
        aria-label="Search products"
      />
    </div>
    <div class="header__cart" aria-label="Shopping cart">
      <a href="cart.html" class="header__cart-link" aria-label="View cart">
        <span class="header__cart-icon">🛒</span>
        <span id="cart-count" class="header__cart-count" aria-live="polite">0</span>
      </a>
      <span id="cart-subtotal" class="header__cart-subtotal" aria-live="polite">$0.00</span>
    </div>
  </div>
</header>
"""

CART_MANAGER_EXAMPLE = """
// Example: Modern cart management with error handling
class CartManager {
  constructor() {
    this.cart = this.loadCart();
    this.updateCartDisplay();
    this.setupEventListeners();
  }
  
  loadCart() {
    try {
      const cartData = localStorage.getItem('cart');
      return cartData ? JSON.parse(cartData) : { items: [] };
    } catch (error) {
      console.error('Error loading cart:', error);
      return { items: [] };
    }
  }
  
  addToCart(product) {
    if (!product || !product.id) {
      console.error('Invalid product data');
      return;
    }
    
    const existingItem = this.cart.items.find(item => item.id === product.id);
    
    if (existingItem) {
      existingItem.quantity += 1;
    } else {
      this.cart.items.push({
        id: product.id,
        name: product.name,
        price: product.price,
        quantity: 1,
        image: product.image || ''
      });
    }
    
    this.saveCart();
    this.updateCartDisplay();
  }
  
  updateCartDisplay() {
    const count = this.cart.items.reduce((sum, item) => sum + item.quantity, 0);
    const subtotal = this.cart.items.reduce(
      (sum, item) => sum + (item.price * item.quantity), 
      0
    );
    
    const countEl = document.getElementById('cart-count');
    const subtotalEl = document.getElementById('cart-subtotal');
    
    if (countEl) countEl.textContent = count;
    if (subtotalEl) subtotalEl.textContent = `$${subtotal.toFixed(2)}`;
  }
  
  saveCart() {
    try {
      localStorage.setItem('cart', JSON.stringify(this.cart));
    } catch (error) {
      console.error('Error saving cart:', error);
    }
  }
  
  setupEventListeners() {
    // Setup event listeners for cart operations
    document.addEventListener('click', (e) => {
      if (e.target.matches('.add-to-cart-btn')) {
        const product = e.target.dataset;
        this.addToCart(product);
      }
    });
  }
}

// Initialize cart manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const cartManager = new CartManager();
  window.cartManager = cartManager; // Make available globally if needed
});
"""

PRODUCT_MANAGER_EXAMPLE = """
// Example: Product manager that loads from products.json and renders to products-container
class ProductManager {
  constructor() {
    this.products = [];
    this.productContainer = document.getElementById('products-container'); // CRITICAL: Use 'products-container' (with 's', plural)
    this.setupEventListeners();
    this.loadProducts();
  }

  async loadProducts() {
    try {
      const response = await fetch('products.json');
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      // Handle both array format and object with products property
      this.products = Array.isArray(data) ? data : (data.products || []);
      this.renderProducts(this.products);
    } catch (error) {
      console.error('Error loading products:', error);
      // Fallback to empty array or error message
      this.products = [];
      if (this.productContainer) {
        this.productContainer.innerHTML = '<p>Error loading products. Please try again later.</p>';
      }
    }
  }

  renderProducts(products) {
    if (!this.productContainer) {
      console.error('Product container not found. Ensure HTML has <div id="products-container"></div>');
      return;
    }
    
    if (!Array.isArray(products)) {
      console.error('Invalid products data');
      return;
    }

    if (products.length === 0) {
      this.productContainer.innerHTML = '<p class="no-products">No products found.</p>';
      return;
    }

    this.productContainer.innerHTML = products.map(product => `
      <article class="product-card" data-category="${product.category}" data-price="${product.price}">
        <div class="product-card__image-wrapper">
          <img src="${product.image}" alt="${product.name}" class="product-card__image" loading="lazy">
        </div>
        <div class="product-card__content">
          <h3 class="product-card__title">${product.name}</h3>
          ${product.description ? `<p class="product-card__description">${product.description}</p>` : ''}
          <div class="product-card__footer">
            <span class="product-card__price">$${product.price.toFixed(2)}</span>
            <button class="product-card__button add-to-cart-btn" 
                    data-id="${product.id}" 
                    data-name="${product.name}" 
                    data-price="${product.price}" 
                    data-image="${product.image}"
                    aria-label="Add ${product.name} to cart">
              Add to Cart
            </button>
          </div>
        </div>
      </article>
    `).join('');
  }

  setupEventListeners() {
    // CRITICAL: Always check if elements exist before attaching event listeners
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', this.debounce(this.handleSearch.bind(this), 300));
    }

    const filterSelect = document.getElementById('filter-select') || document.getElementById('category-filter');
    if (filterSelect) {
      filterSelect.addEventListener('change', this.handleFilter.bind(this));
    }

    const sortSelect = document.getElementById('sort-select') || document.getElementById('sort-by');
    if (sortSelect) {
      sortSelect.addEventListener('change', this.handleSort.bind(this));
    }
  }

  handleSearch(event) {
    const query = event.target.value.toLowerCase();
    const filteredProducts = this.products.filter(product => 
      product.name.toLowerCase().includes(query)
    );
    this.renderProducts(filteredProducts);
  }

  handleFilter(event) {
    const filterValue = event.target.value;
    let filteredProducts = this.products;
    
    if (filterValue !== 'all') {
      filteredProducts = this.products.filter(product => product.category === filterValue);
    }
    
    this.renderProducts(filteredProducts);
  }

  handleSort(event) {
    const sortValue = event.target.value;
    let sortedProducts = [...this.products];

    if (sortValue === 'price-asc') {
      sortedProducts.sort((a, b) => a.price - b.price);
    } else if (sortValue === 'price-desc') {
      sortedProducts.sort((a, b) => b.price - a.price);
    } else if (sortValue === 'name-asc') {
      sortedProducts.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortValue === 'name-desc') {
      sortedProducts.sort((a, b) => b.name.localeCompare(a.name));
    }

    this.renderProducts(sortedProducts);
  }

  debounce(func, wait) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }
}

// Initialize product manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const productManager = new ProductManager();
  window.productManager = productManager; // Make available globally if needed
});
"""

RESPONSIVE_CSS_EXAMPLE = """
/* Example: Premium storefront stylesheet with cohesive design system */
:root {
  --color-primary: #2563eb;
  --color-primary-dark: #1d4ed8;
  --color-secondary: #f97316;
  --color-accent: #14b8a6;
  --color-surface: #ffffff;
  --color-surface-muted: #f5f7fb;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-border: rgba(15, 23, 42, 0.08);
  --gradient-brand: linear-gradient(135deg, #2563eb, #14b8a6);
  --shadow-xs: 0 1px 3px rgba(15, 23, 42, 0.08);
  --shadow-sm: 0 4px 12px rgba(15, 23, 42, 0.12);
  --shadow-md: 0 12px 30px rgba(15, 23, 42, 0.15);
  --shadow-lg: 0 20px 60px rgba(15, 23, 42, 0.18);
  --radius-sm: 0.5rem;
  --radius-md: 0.75rem;
  --radius-lg: 1.5rem;
  --spacing-xs: clamp(0.4rem, 1vw, 0.5rem);
  --spacing-sm: clamp(0.6rem, 1vw, 0.75rem);
  --spacing-md: clamp(1rem, 1.5vw, 1.5rem);
  --spacing-lg: clamp(1.5rem, 2vw, 2.5rem);
  --spacing-xl: clamp(2rem, 3vw, 4rem);
  --font-heading: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
  --font-body: "General Sans", "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
  --transition-base: 0.25s ease;
  --blur-glass: 18px;
  --container-max: 1200px;
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: var(--font-body);
  color: var(--color-text);
  background: var(--color-surface-muted);
  min-height: 100vh;
  line-height: 1.6;
}

main {
  width: min(100%, var(--container-max));
  margin: 0 auto;
  padding: var(--spacing-xl) clamp(1rem, 4vw, 2rem);
}

a {
  color: inherit;
  text-decoration: none;
}

a:hover,
a:focus-visible {
  color: var(--color-primary);
}

img {
  display: block;
  width: 100%;
  height: auto;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  border: 0;
}

button,
input,
select,
textarea {
  font-family: inherit;
}

button {
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* Shared header using canonical .header and .header__* classes */
.header {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(var(--blur-glass));
  border-bottom: 1px solid var(--color-border);
  box-shadow: var(--shadow-xs);
}

.header__container {
  width: min(100%, var(--container-max));
  margin: 0 auto;
  padding: var(--spacing-sm) clamp(1rem, 4vw, 2rem);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.header__logo {
  font-size: 1.2rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.header__nav {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: var(--spacing-sm);
}

.header__nav a {
  padding: 0.5rem 0.9rem;
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  transition: background var(--transition-base), color var(--transition-base);
}

.header__nav a:hover,
.header__nav a:focus-visible,
.header__nav a[aria-current="page"] {
  background: rgba(37, 99, 235, 0.12);
  color: var(--color-primary);
}

.header__actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.header__search-input {
  min-width: 220px;
  padding: 0.45rem 0.75rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
}

.header__search-input:focus-visible {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.25);
}

.header__cart {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.75rem;
  border-radius: var(--radius-sm);
  background: rgba(15, 23, 42, 0.04);
  font-weight: 500;
}

.hero {
  margin-top: var(--spacing-xl);
  padding: var(--spacing-xl);
  border-radius: var(--radius-lg);
  background: var(--gradient-brand);
  color: white;
  display: grid;
  gap: var(--spacing-md);
  box-shadow: var(--shadow-md);
}

.hero h1 {
  font-family: var(--font-heading);
  font-size: clamp(2rem, 5vw, 3rem);
  margin: 0;
}

.hero p {
  max-width: 45ch;
  opacity: 0.92;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.cta-button {
  border: none;
  background: white;
  color: var(--color-primary-dark);
  padding: 0.85rem 1.5rem;
  border-radius: 999px;
  font-weight: 600;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  box-shadow: var(--shadow-sm);
}

.cta-button.secondary {
  background: transparent;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.4);
}

.cta-button:hover,
.cta-button:focus-visible {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.filters {
  margin-top: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  align-items: center;
}

.filters select,
.filters .pill {
  min-width: 180px;
  padding: 0.55rem 0.9rem;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-surface-muted);
}

#products-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: clamp(1rem, 2.5vw, 2rem);
  margin-top: var(--spacing-md);
}

.product-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition-base), box-shadow var(--transition-base);
  isolation: isolate;
}

.product-card::after {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(130deg, rgba(37, 99, 235, 0.08), transparent 70%);
  opacity: 0;
  transition: opacity var(--transition-base);
  z-index: -1;
}

.product-card:hover {
  transform: translateY(-6px);
  box-shadow: var(--shadow-lg);
}

.product-card:hover::after {
  opacity: 1;
}

.product-card__image-wrapper {
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 4 / 3;
  margin-bottom: var(--spacing-sm);
  background: radial-gradient(circle at top, rgba(37, 99, 235, 0.1), rgba(15, 23, 42, 0.08));
}

.product-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--transition-base);
}

.product-card:hover .product-card__image {
  transform: scale(1.05);
}

.product-card__title {
  font-size: 1.1rem;
  margin: 0;
  color: var(--color-text);
}

.product-card__description {
  color: var(--color-text-muted);
  font-size: 0.95rem;
  margin: 0;
  min-height: 3rem;
}

.product-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: var(--spacing-sm);
  border-top: 1px solid var(--color-border);
  gap: var(--spacing-sm);
}

.product-card__price {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-primary-dark);
}

.product-card__button {
  border: none;
  border-radius: var(--radius-sm);
  padding: 0.6rem 1.2rem;
  background: var(--color-primary);
  color: white;
  font-weight: 600;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.product-card__button:hover,
.product-card__button:focus-visible {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.product-card__badge {
  position: absolute;
  top: 1rem;
  left: 1rem;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.9);
  color: white;
  font-size: 0.75rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.product-card--loading {
  animation: shimmer 1.4s linear infinite;
  background: linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.05) 75%);
  background-size: 200% 100%;
}

.cart-layout {
  display: grid;
  gap: var(--spacing-lg);
  grid-template-columns: 1fr;
}

.cart-summary-card,
.cart-table {
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-sm);
  padding: var(--spacing-md);
}

.cart-table__header,
.cart-table__row {
  display: grid;
  grid-template-columns: 2fr repeat(3, 1fr);
  gap: var(--spacing-sm);
  align-items: center;
}

.cart-table__header {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--spacing-xs);
}

.checkout-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.form-section {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-sm);
}

.form-section h2 {
  margin-top: 0;
  font-family: var(--font-heading);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: var(--spacing-md);
}

.form-field {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: 0.65rem 0.85rem;
  background: var(--color-surface-muted);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.form-field:focus-visible {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
  outline: none;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: grid;
  place-items: center;
  z-index: 50;
}

.modal {
  width: min(90vw, 480px);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.45s var(--transition-base);
}

.toast {
  position: fixed;
  bottom: 1.5rem;
  right: 1.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1.2rem;
  border-radius: var(--radius-md);
  background: rgba(15, 23, 42, 0.85);
  color: white;
  box-shadow: var(--shadow-md);
}

@media (max-width: 992px) {
  .header__container {
    flex-wrap: wrap;
  }

  .header__nav {
    order: 3;
    width: 100%;
    justify-content: space-between;
  }

  .filters {
    flex-direction: column;
    align-items: stretch;
  }

  .cart-table__header,
  .cart-table__row {
    grid-template-columns: 1.5fr repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  #products-container {
    grid-template-columns: 1fr;
  }

  .hero {
    padding: var(--spacing-lg);
  }
}

@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes slideUp {
  from {
    transform: translateY(20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto;
  }
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-surface: #0f172a;
    --color-surface-muted: #111c34;
    --color-text: #f8fafc;
    --color-text-muted: #94a3b8;
    --color-border: rgba(148, 163, 184, 0.2);
  }

  body {
    background: radial-gradient(circle at top, rgba(37, 99, 235, 0.35), rgba(15, 23, 42, 1));
  }

  .header {
    background: rgba(15, 23, 42, 0.85);
  }

  .product-card,
  .form-section,
  .cart-summary-card,
  .cart-table,
  .modal {
    background: rgba(15, 23, 42, 0.9);
    box-shadow: var(--shadow-sm);
  }

  .filters {
    background: rgba(15, 23, 42, 0.85);
  }
}
"""

CODE_EXAMPLES = {
    "header": HEADER_EXAMPLE,
    "cart_manager": CART_MANAGER_EXAMPLE,
    "product_manager": PRODUCT_MANAGER_EXAMPLE,
    "responsive_css": RESPONSIVE_CSS_EXAMPLE,
}


def get_code_example(example_name: str) -> str:
    """Get a code example by name."""
    return CODE_EXAMPLES.get(example_name, "")


def get_relevant_examples(filename: str, file_type: str) -> str:
    """Get relevant code examples based on filename and type."""
    examples = []
    
    if file_type.lower() in ["html", "htm"]:
        if "header" in filename.lower() or "nav" in filename.lower():
            examples.append(("Header Component", get_code_example("header")))
    
    if file_type.lower() in ["js", "javascript"]:
        if "cart" in filename.lower() or "script" in filename.lower():
            examples.append(("Cart Manager", get_code_example("cart_manager")))
            examples.append(("Product Manager", get_code_example("product_manager")))
    
    if file_type.lower() == "css":
        examples.append(("Responsive CSS", get_code_example("responsive_css")))
    
    if not examples:
        return ""
    
    result_parts = []
    for name, code in examples:
        result_parts.append(f"--- {name} Example ---")
        result_parts.append(code)
        result_parts.append("")
    
    return "\n".join(result_parts)


def _get_critical_notes(filename: str, file_type: str) -> list[str]:
    """Return file-specific reminders that must be injected into the codegen prompt."""

    notes: list[str] = []
    name_lower = filename.lower()
    type_lower = file_type.lower()

    if type_lower in {"html", "htm"}:
        notes.append(
            "Use the shared header/footer exactly as defined (logo linking to index.html, nav links to all pages, #search-input, #cart-count, #cart-subtotal, shared CSS/JS)."
        )
        notes.append(
            "Header navigation MUST expose direct links to shop.html, cart.html, checkout.html, and about.html; include all anchors so users can click through."
        )
        if "checkout" in name_lower:
            notes.append(
                "Checkout page must include order summary containers (e.g., #checkout-summary, #order-total), shipping/billing forms (#checkout-form), payment method selectors, and a primary submission button wired for future JS."
            )

        if "about" in name_lower:
            notes.append(
                "About page should highlight brand story/mission, sustainability or quality pillars, team or store locations, and clear CTAs to shop/cart; reuse shared header/footer and keep content sections semantic."
            )

        if "cart" in name_lower:
            notes.append(
                "Cart page must expose #cart-items (or similar) plus empty-state messaging, per-item quantity controls, and totals (#cart-subtotal/#cart-total) bound to localStorage—do NOT hardcode the table rows."
            )

        if any(page in name_lower for page in ("index", "shop")):
            notes.append(
                "Product listing pages MUST expose an empty <section id=\"products-container\"></section> (no hardcoded <article class=\"product-card\"> markup in HTML); JavaScript renders all cards from products.json."
            )

        if "shop" in name_lower:
            notes.append(
                "Place visible filter and sort controls above the product container (filter select id=\"filter-select\" or id=\"category-filter\" covering all categories, sort select id=\"sort-select\" or id=\"sort-by\" with price/name options)."
            )
            notes.append(
                "Filter <option value=\"...\"> attributes MUST exactly match the CATEGORIES entries from the PM spec (or their data-category equivalents) so that JavaScript can reliably compare select.value to product.category."
            )

        if "cart" in name_lower:
            notes.append(
                "Cart pages must render a dynamic table/list bound to localStorage results; do NOT seed static line items or totals—provide containers like <div id=\"cart-items\"></div> for JavaScript to fill."
            )

    if type_lower in {"json"} or name_lower.endswith("products.json"):
        notes.append(
            "Populate products.json with the actual catalog (array or {\"products\": [...]}) including id, name, price, category, description, and image for every item referenced by the Product Manager brief—never leave placeholders."
        )

    if type_lower in {"js", "javascript"} or name_lower.endswith("script.js"):
        notes.append(
            "Wire JavaScript to the shared DOM IDs/classes: fetch('products.json'), inject into #products-container, debounce #search-input, watch #filter-select/#category-filter and #sort-select/#sort-by, and ensure add-to-cart buttons use class \"add-to-cart-btn\" so CartManager updates #cart-count/#cart-subtotal."
        )
        notes.append(
            "Ensure cart and checkout views are driven entirely from localStorage cart data and PRODUCT_DATA_LOCATION (e.g., products.json): populate #cart-items, #cart-subtotal/#cart-total, #checkout-summary, and related totals dynamically instead of hardcoding example line items."
        )

    return notes

