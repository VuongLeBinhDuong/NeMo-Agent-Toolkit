/**
 * script.js
 * Fashion Marketplace Interactivity and State Management
 */

// Constants
const PRODUCT_DATA_LOCATION = 'products.json';

// Utility Functions
/**
 * Debounce function to limit the rate at which a function is executed.
 * @param {Function} func - The function to debounce.
 * @param {number} wait - The delay in milliseconds.
 * @returns {Function} - The debounced function.
 */
const debounce = (func, wait) => {
  let timeout;
  return function(...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
};

// Classes
/**
 * Manages the product listing and filtering/sorting.
 */
class ProductManager {
  constructor() {
    this.products = [];
    this.filteredProducts = [];
    this.productContainer = document.getElementById('products-container');
    this.setupEventListeners();
    this.loadProducts();
  }

  /**
   * Loads products from the JSON file.
   * @async
   */
  async loadProducts() {
    try {
      const response = await fetch(PRODUCT_DATA_LOCATION);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      this.products = Array.isArray(data) ? data : (data.products || []);
      this.filteredProducts = [...this.products];
      this.renderProducts(this.filteredProducts);
    } catch (error) {
      console.error('Error loading products:', error);
      if (this.productContainer) {
        this.productContainer.innerHTML = '<p>Error loading products. Please try again later.</p>';
      }
    }
  }

  /**
   * Renders products to the DOM.
   * @param {Array} products - The list of products to render.
   */
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

  /**
   * Sets up event listeners for search, filter, and sort.
   */
  setupEventListeners() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      searchInput.addEventListener('input', debounce(this.handleSearch.bind(this), 300));
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

  /**
   * Handles search input to filter products.
   * @param {Event} event - The input event.
   */
  handleSearch(event) {
    const query = event.target.value.toLowerCase();
    this.filteredProducts = this.products.filter(product => 
      product.name.toLowerCase().includes(query)
    );
    this.renderProducts(this.filteredProducts);
  }

  /**
   * Handles filter selection to filter products by category.
   * @param {Event} event - The change event.
   */
  handleFilter(event) {
    const filterValue = event.target.value;
    if (filterValue === 'all') {
      this.filteredProducts = [...this.products];
    } else {
      this.filteredProducts = this.products.filter(product => product.category === filterValue);
    }
    this.renderProducts(this.filteredProducts);
  }

  /**
   * Handles sort selection to sort products.
   * @param {Event} event - The change event.
   */
  handleSort(event) {
    const sortValue = event.target.value;
    this.filteredProducts = [...this.filteredProducts];

    if (sortValue === 'price-asc') {
      this.filteredProducts.sort((a, b) => a.price - b.price);
    } else if (sortValue === 'price-desc') {
      this.filteredProducts.sort((a, b) => b.price - a.price);
    } else if (sortValue === 'name-asc') {
      this.filteredProducts.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortValue === 'name-desc') {
      this.filteredProducts.sort((a, b) => b.name.localeCompare(a.name));
    }

    this.renderProducts(this.filteredProducts);
  }
}

/**
 * Manages the shopping cart.
 */
class CartManager {
  constructor() {
    this.cart = this.loadCart();
    this.updateCartDisplay();
    this.setupEventListeners();
  }

  /**
   * Loads cart data from localStorage.
   * @returns {Object} - The cart data.
   */
  loadCart() {
    try {
      const cartData = localStorage.getItem('cart');
      return cartData ? JSON.parse(cartData) : { items: [] };
    } catch (error) {
      console.error('Error loading cart:', error);
      return { items: [] };
    }
  }

  /**
   * Adds a product to the cart.
   * @param {Object} product - The product to add.
   */
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

  /**
   * Updates the cart display in the UI.
   */
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

  /**
   * Saves the cart data to localStorage.
   */
  saveCart() {
    try {
      localStorage.setItem('cart', JSON.stringify(this.cart));
    } catch (error) {
      console.error('Error saving cart:', error);
    }
  }

  /**
   * Sets up event listeners for adding items to the cart.
   */
  setupEventListeners() {
    document.addEventListener('click', (e) => {
      if (e.target.matches('.add-to-cart-btn')) {
        const product = e.target.dataset;
        this.addToCart(product);
      }
    });
  }
}

/**
 * Manages modal dialogs.
 */
class Modal {
  constructor(modalId) {
    this.modal = document.getElementById(modalId);
    this.openButton = document.querySelector(`[data-modal-open="${modalId}"]`);
    this.closeButton = document.querySelector(`[data-modal-close="${modalId}"]`);
    this.setupEventListeners();
  }

  /**
   * Sets up event listeners for opening and closing the modal.
   */
  setupEventListeners() {
    if (this.openButton) {
      this.openButton.addEventListener('click', this.open.bind(this));
    }

    if (this.closeButton) {
      this.closeButton.addEventListener('click', this.close.bind(this));
    }

    if (this.modal) {
      this.modal.addEventListener('click', (e) => {
        if (e.target === this.modal) {
          this.close();
        }
      });
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.close();
      }
    });
  }

  /**
   * Opens the modal.
   */
  open() {
    if (this.modal) {
      this.modal.style.display = 'block';
      this.focusFirstElement();
    }
  }

  /**
   * Closes the modal.
   */
  close() {
    if (this.modal) {
      this.modal.style.display = 'none';
    }
  }

  /**
   * Focuses the first focusable element in the modal.
   */
  focusFirstElement() {
    const focusableElements = this.modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusableElements.length) {
      focusableElements[0].focus();
    }
  }
}

// Initialize Managers
document.addEventListener('DOMContentLoaded', () => {
  const productManager = new ProductManager();
  const cartManager = new CartManager();
  const modal = new Modal('cart-modal');

  window.productManager = productManager; // Make available globally if needed
  window.cartManager = cartManager; // Make available globally if needed
  window.modal = modal; // Make available globally if needed
});