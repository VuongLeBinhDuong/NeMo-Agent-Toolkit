// script.js for tech-gadget-store project

/**
 * Class to manage product operations including loading, filtering, and sorting.
 */
class ProductManager {
  /**
   * Initializes the ProductManager, sets up event listeners, and loads products.
   */
  constructor() {
    this.products = [];
    this.productContainer = document.getElementById('products-container');
    this.setupEventListeners();
    this.loadProducts();
  }

  /**
   * Asynchronously loads products from products.json and renders them.
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
   * Renders the list of products to the product container.
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
   * Sets up event listeners for search, filter, and sort functionalities.
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
   * Filters products based on the search query.
   * @param {Event} event - The input event from the search input.
   */
  handleSearch(event) {
    const query = event.target.value.toLowerCase();
    const filteredProducts = this.products.filter(product => 
      product.name.toLowerCase().includes(query)
    );
    this.renderProducts(filteredProducts);
  }

  /**
   * Filters products based on the selected category.
   * @param {Event} event - The change event from the filter select.
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
   * Sorts products based on the selected sort option.
   * @param {Event} event - The change event from the sort select.
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
   * Debounces a function to limit its execution rate.
   * @param {Function} func - The function to debounce.
   * @param {number} wait - The wait time in milliseconds.
   * @returns {Function} - The debounced function.
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
 * Class to manage cart operations including adding, updating, and saving cart items.
 */
class CartManager {
  /**
   * Initializes the CartManager, loads the cart, updates the cart display, and sets up event listeners.
   */
  constructor() {
    this.cart = this.loadCart();
    this.updateCartDisplay();
    this.setupEventListeners();
  }

  /**
   * Loads the cart from localStorage.
   * @returns {Object} - The cart object.
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
   * Saves the cart to localStorage.
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
 * Class to manage modal operations including opening, closing, and focus trapping.
 */
class Modal {
  /**
   * Initializes the Modal, sets up event listeners, and manages focus trapping.
   * @param {string} modalId - The ID of the modal element.
   */
  constructor(modalId) {
    this.modal = document.getElementById(modalId);
    if (!this.modal) {
      console.error(`Modal with ID ${modalId} not found.`);
      return;
    }
    this.openButton = document.querySelector(`[data-modal-target="${modalId}"]`);
    this.closeButton = this.modal.querySelector('[data-close-button]');
    this.overlay = document.getElementById('overlay');
    this.focusableElements = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    this.firstFocusableElement = null;
    this.lastFocusableElement = null;
    this.setupEventListeners();
  }

  /**
   * Sets up event listeners for opening, closing, and focus trapping.
   */
  setupEventListeners() {
    if (this.openButton) {
      this.openButton.addEventListener('click', this.openModal.bind(this));
    }
    if (this.closeButton) {
      this.closeButton.addEventListener('click', this.closeModal.bind(this));
    }
    if (this.overlay) {
      this.overlay.addEventListener('click', this.closeModal.bind(this));
    }
    document.addEventListener('keydown', this.handleKeyDown.bind(this));
  }

  /**
   * Opens the modal and sets up focus trapping.
   */
  openModal() {
    if (!this.modal) return;
    this.modal.classList.add('active');
    this.overlay.classList.add('active');
    this.focusableElements = this.modal.querySelectorAll(this.focusableElements);
    this.firstFocusableElement = this.focusableElements[0];
    this.lastFocusableElement = this.focusableElements[this.focusableElements.length - 1];
    this.firstFocusableElement.focus();
  }

  /**
   * Closes the modal.
   */
  closeModal() {
    if (!this.modal) return;
    this.modal.classList.remove('active');
    this.overlay.classList.remove('active');
  }

  /**
   * Handles keydown events for focus trapping and closing the modal.
   * @param {Event} event - The keydown event.
   */
  handleKeyDown(event) {
    if (!this.modal || !this.modal.classList.contains('active')) return;
    if (event.key === 'Escape') {
      this.closeModal();
    } else if (event.key === 'Tab') {
      this.handleTabKey(event);
    }
  }

  /**
   * Handles tab key events for focus trapping.
   * @param {Event} event - The keydown event.
   */
  handleTabKey(event) {
    if (event.shiftKey) {
      if (document.activeElement === this.firstFocusableElement) {
        event.preventDefault();
        this.lastFocusableElement.focus();
      }
    } else {
      if (document.activeElement === this.lastFocusableElement) {
        event.preventDefault();
        this.firstFocusableElement.focus();
      }
    }
  }
}

/**
 * Class to manage checkout form submission and validation.
 */
class CheckoutManager {
  /**
   * Initializes the CheckoutManager, sets up event listeners, and manages form validation.
   */
  constructor() {
    this.form = document.getElementById('checkout-form');
    if (!this.form) {
      console.error('Checkout form not found.');
      return;
    }
    this.setupEventListeners();
  }

  /**
   * Sets up event listeners for form submission.
   */
  setupEventListeners() {
    this.form.addEventListener('submit', this.handleSubmit.bind(this));
  }

  /**
   * Handles form submission, validates inputs, and processes the checkout.
   * @param {Event} event - The form submit event.
   */
  handleSubmit(event) {
    event.preventDefault();
    if (this.validateForm()) {
      this.processCheckout();
    }
  }

  /**
   * Validates the checkout form inputs.
   * @returns {boolean} - True if the form is valid, false otherwise.
   */
  validateForm() {
    const name = this.form.name.value.trim();
    const email = this.form.email.value.trim();
    const address = this.form.address.value.trim();
    const city = this.form.city.value.trim();
    const state = this.form.state.value.trim();
    const zip = this.form.zip.value.trim();
    const cardNumber = this.form.cardNumber.value.trim();
    const cardExpiry = this.form.cardExpiry.value.trim();
    const cardCVC = this.form.cardCVC.value.trim();

    if (!name) {
      this.showError(this.form.name, 'Name is required');
      return false;
    }
    if (!email || !/\S+@\S+\.\S+/.test(email)) {
      this.showError(this.form.email, 'Valid email is required');
      return false;
    }
    if (!address) {
      this.showError(this.form.address, 'Address is required');
      return false;
    }
    if (!city) {
      this.showError(this.form.city, 'City is required');
      return false;
    }
    if (!state) {
      this.showError(this.form.state, 'State is required');
      return false;
    }
    if (!zip || !/^\d{5}(-\d{4})?$/.test(zip)) {
      this.showError(this.form.zip, 'Valid ZIP code is required');
      return false;
    }
    if (!cardNumber || !/^\d{16}$/.test(cardNumber)) {
      this.showError(this.form.cardNumber, 'Valid card number is required');
      return false;
    }
    if (!cardExpiry || !/^(0[1-9]|1[0-2])\/\d{2}$/.test(cardExpiry)) {
      this.showError(this.form.cardExpiry, 'Valid card expiry date is required');
      return false;
    }
    if (!cardCVC || !/^\d{3}$/.test(cardCVC)) {
      this.showError(this.form.cardCVC, 'Valid CVC is required');
      return false;
    }

    this.clearErrors();
    return true;
  }

  /**
   * Shows an error message for a form field.
   * @param {HTMLElement} field - The form field element.
   * @param {string} message - The error message to display.
   */
  showError(field, message) {
    const errorElement = field.nextElementSibling;
    if (errorElement && errorElement.classList.contains('error-message')) {
      errorElement.textContent = message;
    } else {
      const errorElement = document.createElement('div');
      errorElement.className = 'error-message';
      errorElement.textContent = message;
      field.parentNode.insertBefore(errorElement, field.nextSibling);
    }
  }

  /**
   * Clears all error messages from the form.
   */
  clearErrors() {
    const errorElements = this.form.querySelectorAll('.error-message');
    errorElements.forEach(errorElement => errorElement.remove());
  }

  /**
   * Processes the checkout by clearing the cart and showing a success message.
   */
  processCheckout() {
    const cartManager = new CartManager();
    cartManager.cart.items = [];
    cartManager.saveCart();
    cartManager.updateCartDisplay();
    alert('Checkout successful! Thank you for your purchase.');
    this.form.reset();
  }
}

// Initialize product manager, cart manager, and checkout manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const productManager = new ProductManager();
  const cartManager = new CartManager();
  const checkoutManager = new CheckoutManager();
  window.productManager = productManager;
  window.cartManager = cartManager;
  window.checkoutManager = checkoutManager;
});