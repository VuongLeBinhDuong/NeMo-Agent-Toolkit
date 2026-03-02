document.addEventListener('DOMContentLoaded', () => {
  const productsContainer = document.getElementById('products-container');
  const categoryFilter = document.getElementById('category-filter');
  const sortBySelect = document.getElementById('sort-by');
  const cartItemsContainer = document.getElementById('cart-items');
  const cartTotalElement = document.getElementById('cart-total');

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
      const cartData = JSON.parse(localStorage.getItem('cart')) || { items: [] };
      let total = 0;
      cartItemsContainer.innerHTML = '';
      cartData.items.forEach(item => {
        const cartItem = document.createElement('div');
        cartItem.classList.add('cart-item');
        cartItem.innerHTML = `
          <span>${item.name} x ${item.quantity}</span>
          <span>$${(item.price * item.quantity).toFixed(2)}</span>
        `;
        cartItemsContainer.appendChild(cartItem);
        total += item.price * item.quantity;
      });
      if (cartTotalElement) {
        cartTotalElement.textContent = `$${total.toFixed(2)}`;
      }
    }
  }

  function addToCart(productId, quantity = 1) {
    const cartData = JSON.parse(localStorage.getItem('cart')) || { items: [] };
    const existingItem = cartData.items.find(item => item.id === productId);
    if (existingItem) {
      existingItem.quantity += quantity;
    } else {
      const product = products.find(p => p.id === productId);
      cartData.items.push({ ...product, quantity });
    }
    localStorage.setItem('cart', JSON.stringify(cartData));
    updateCartDisplay();
  }

  if (categoryFilter) {
    categoryFilter.addEventListener('change', () => {
      const selectedCategory = categoryFilter.value;
      const filteredProducts = products.filter(product =>
        selectedCategory === 'all' ? true : product.category === selectedCategory
      );
      renderProducts(filteredProducts);
    });
  }

  if (sortBySelect) {
    sortBySelect.addEventListener('change', () => {
      const selectedSortBy = sortBySelect.value;
      let sortedProducts = [...products];
      switch (selectedSortBy) {
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

  if (cartItemsContainer) {
    cartItemsContainer.addEventListener('click', event => {
      if (event.target.tagName === 'BUTTON') {
        const productId = Number(event.target.dataset.productId);
        const quantityChange = Number(event.target.dataset.quantityChange);
        addToCart(productId, quantityChange);
      }
    });
  }

  const urlParams = new URLSearchParams(window.location.search);
  const productId = urlParams.get('id');
  if (productId) {
    const product = products.find(p => p.id === Number(productId));
    if (product) {
      document.getElementById('product-detail').innerHTML = `
        <img src="${product.image}" alt="${product.name}" class="product-detail__image">
        <h2 class="product-detail__title">${product.name}</h2>
        <p class="product-detail__description">${product.description}</p>
        <p class="product-detail__price">$${product.price.toFixed(2)}</p>
        <button id="add-to-cart" data-product-id="${product.id}" data-quantity-change="1">Add to Cart</button>
      `;
      document.getElementById('add-to-cart').addEventListener('click', () => {
        addToCart(Number(productId));
      });
    } else {
      document.getElementById('product-detail').innerHTML = '<p>Product not found</p>';
    }
  }
});