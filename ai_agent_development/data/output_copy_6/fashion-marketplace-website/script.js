// script.js for fashion-marketplace-website

/**
 * ProductManager class to handle product data loading, rendering, and filtering.
 */
class ProductManager {
  /**
   * Constructor for ProductManager.
   */
  constructor() {
    /** @type {Array} */
    this.products = [];
    /** @type {HTMLElement} */
    this.productContainer = document.getElementById('products-container');
    this.setupEventListeners();
    this.loadProducts();
  }

  /**
   * Loads products from products.json.
   * @async
   */
  async loadProducts() {
    try {
      const response = await fetch('products.json');
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      this.products = Array.isArray(data) ? data : (data.products || []);
      this.renderProducts(this.products);
    } catch (error) {
      console.error('Error loading products:', error);
      if (this.productContainer) {
        this.productContainer.innerHTML = '<p>Error loading products. Please try again later.</p>';
      }
    }
  }

  /**
   * Renders products to the product container.
   * @param {Array} products - Array of product objects.
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

  /**
   * Handles search input.
   * @param {Event} event - Input event.
   */
  handleSearch(event) {
    const query = event.target.value.toLowerCase();
    const filteredProducts = this.products.filter(product => 
      product.name.toLowerCase().includes(query)
    );
    this.renderProducts(filteredProducts);
  }

  /**
   * Handles category filter change.
   * @param {Event} event - Change event.
   */
  handleFilter(event) {
    const filterValue = event.target.value;
    let filteredProducts = this.products;
    
    if (filterValue !== 'all') {
      filteredProducts = this.products.filter(product => product.category === filterValue);
    }
    
    this.renderProducts(filteredProducts);
  }

  /**
   * Handles sort change.
   * @param {Event} event - Change event.
   */
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

  /**
   * Debounces a function.
   * @param {Function} func - Function to debounce.
   * @param {number} wait - Wait time in milliseconds.
   * @returns {Function} - Debounced function.
   */
  debounce(func, wait) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }
}

/**
 * CartManager class to handle cart operations.
 */
class CartManager {
  /**
   * Constructor for CartManager.
   */
  constructor() {
    /** @type {Object} */
    this.cart = this.loadCart();
    this.updateCartDisplay();
    this.setupEventListeners();
  }

  /**
   * Loads cart data from localStorage.
   * @returns {Object} - Cart data.
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
   * @param {Object} product - Product data.
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
   * Saves cart data to localStorage.
   */
  saveCart() {
    try {
      localStorage.setItem('cart', JSON.stringify(this.cart));
    } catch (error) {
      console.error('Error saving cart:', error);
    }
  }

  /**
   * Sets up event listeners for add-to-cart buttons.
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
 * Modal class to handle modal dialog management.
 */
class Modal {
  /**
   * Constructor for Modal.
   * @param {string} selector - Selector for the modal element.
   */
  constructor(selector) {
    /** @type {HTMLElement} */
    this.modal = document.querySelector(selector);
    if (!this.modal) {
      console.error('Modal element not found. Ensure HTML has the modal element.');
      return;
    }
    this.setupEventListeners();
  }

  /**
   * Sets up event listeners for modal.
   */
  setupEventListeners() {
    const closeButton = this.modal.querySelector('.modal-close');
    if (closeButton) {
      closeButton.addEventListener('click', this.close.bind(this));
    }

    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });

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
      this.modal.querySelector('.modal-content').focus();
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
}

// Initialize product and cart managers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const productManager = new ProductManager();
  const cartManager = new CartManager();
  window.productManager = productManager;
  window.cartManager = cartManager;
});