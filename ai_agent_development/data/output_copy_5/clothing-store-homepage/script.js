/**
 * ProductManager class responsible for loading, filtering, sorting, and rendering products.
 */
class ProductManager {
  /**
   * Initializes the ProductManager, sets up event listeners, and loads products.
   */
  constructor() {
    this.products = [];
    this.filteredProducts = [];
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
   * Renders products to the product container.
   * @param {Array} products - Array of product objects to render.
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
   * Filters products based on search query.
   * @param {Event} event - Input event from search input.
   */
  handleSearch(event) {
    const query = event.target.value.toLowerCase();
    this.filteredProducts = this.products.filter(product => 
      product.name.toLowerCase().includes(query)
    );
    this.renderProducts(this.filteredProducts);
  }

  /**
   * Filters products based on selected category.
   * @param {Event} event - Change event from filter select.
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
   * Sorts products based on selected criteria.
   * @param {Event} event - Change event from sort select.
   */
  handleSort(event) {
    const sortValue = event.target.value;
    this.filteredProducts = [...this.filteredProducts];

    switch (sortValue) {
      case 'price-asc':
        this.filteredProducts.sort((a, b) => a.price - b.price);
        break;
      case 'price-desc':
        this.filteredProducts.sort((a, b) => b.price - a.price);
        break;
      case 'name-asc':
        this.filteredProducts.sort((a, b) => a.name.localeCompare(b.name));
        break;
      case 'name-desc':
        this.filteredProducts.sort((a, b) => b.name.localeCompare(a.name));
        break;
      default:
        break;
    }

    this.renderProducts(this.filteredProducts);
  }

  /**
   * Debounces a function to limit its execution rate.
   * @param {Function} func - Function to debounce.
   * @param {number} wait - Time to wait before executing the function.
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
 * CartManager class responsible for managing the shopping cart.
 */
class CartManager {
  /**
   * Initializes the CartManager, loads the cart, updates the display, and sets up event listeners.
   */
  constructor() {
    this.cart = this.loadCart();
    this.updateCartDisplay();
    this.setupEventListeners();
  }

  /**
   * Loads the cart from localStorage.
   * @returns {Object} - Cart object with items array.
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
   * @param {Object} product - Product object to add.
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
   * Updates the cart display on the page.
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

// Initialize product and cart managers when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const productManager = new ProductManager();
  const cartManager = new CartManager();
  window.productManager = productManager; // Make available globally if needed
  window.cartManager = cartManager; // Make available globally if needed
});