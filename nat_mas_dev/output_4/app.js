document.addEventListener('DOMContentLoaded', () => {
  const productsContainer = document.getElementById('products-container');
  const categoryFilter = document.getElementById('category-filter');
  const sortBy = document.getElementById('sort-by');
  const searchInput = document.getElementById('search-input');
  const cartItemsContainer = document.getElementById('cart-items');
  const cartCount = document.getElementById('cart-count');
  const cartSubtotal = document.getElementById('cart-subtotal');

  let products = [];

  fetch('products.json')
    .then(response => response.json())
    .then(data => {
      products = data.products;
      renderProducts(products);
      updateCartDisplay();
    });

  function renderProducts(filteredProducts) {
    productsContainer.innerHTML = '';
    filteredProducts.forEach(product => {
      const productCard = document.createElement('div');
      productCard.classList.add('product-card');
      productCard.innerHTML = `
        <h3 class="product-card__title">${product.name}</h3>
        <p class="product-card__description">${product.description}</p>
        <p class="product-card__price">$${product.price.toFixed(2)}</p>
        <a href="product-detail.html?id=${product.id}" class="product-card__link">View Details</a>
      `;
      productsContainer.appendChild(productCard);
    });
  }

  function updateCartDisplay() {
    if (cartItemsContainer) {
      const cart = JSON.parse(localStorage.getItem('cart')) || { items: [] };
      let total = 0;
      cart.items.forEach(item => {
        total += item.price * item.quantity;
      });
      cartCount.textContent = cart.items.length;
      cartSubtotal.textContent = `$${total.toFixed(2)}`;
      cartItemsContainer.innerHTML = '';
      cart.items.forEach(item => {
        const cartItem = document.createElement('div');
        cartItem.classList.add('cart-item');
        cartItem.innerHTML = `
          <span>${item.name} x ${item.quantity}</span>
          <span>$${(item.price * item.quantity).toFixed(2)}</span>
        `;
        cartItemsContainer.appendChild(cartItem);
      });
    }
  }

  if (categoryFilter) {
    categoryFilter.addEventListener('change', () => {
      const selectedCategory = categoryFilter.value;
      const filteredProducts = products.filter(product =>
        selectedCategory === 'all' || product.category === selectedCategory
      );
      renderProducts(filteredProducts);
    });
  }

  if (sortBy) {
    sortBy.addEventListener('change', () => {
      const sortOption = sortBy.value;
      let sortedProducts = [...products];
      switch (sortOption) {
        case 'price-asc':
          sortedProducts.sort((a, b) => a.price - b.price);
          break;
        case 'price-desc':
          sortedProducts.sort((a, b) => b.price - a.price);
          break;
        case 'name-asc':
          sortedProducts.sort((a, b) => a.name.localeCompare(b.name));
          break;
        case 'name-desc':
          sortedProducts.sort((a, b) => b.name.localeCompare(a.name));
          break;
      }
      renderProducts(sortedProducts);
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const searchTerm = searchInput.value.toLowerCase();
      const filteredProducts = products.filter(product =>
        product.name.toLowerCase().includes(searchTerm) ||
        product.description.toLowerCase().includes(searchTerm)
      );
      renderProducts(filteredProducts);
    });
  }

  document.getElementById('add-to-cart').addEventListener('click', () => {
    const productId = parseInt(new URLSearchParams(window.location.search).get('id'));
    const product = products.find(p => p.id === productId);
    if (product) {
      let cart = JSON.parse(localStorage.getItem('cart')) || { items: [] };
      const existingItem = cart.items.find(item => item.id === productId);
      if (existingItem) {
        existingItem.quantity++;
      } else {
        cart.items.push({ ...product, quantity: 1 });
      }
      localStorage.setItem('cart', JSON.stringify(cart));
      updateCartDisplay();
    }
  });
});