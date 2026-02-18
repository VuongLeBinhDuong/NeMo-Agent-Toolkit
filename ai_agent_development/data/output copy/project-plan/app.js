// app.js

document.addEventListener('DOMContentLoaded', () => {
    const products = [
        { id: 1, name: 'Smartphone XYZ', category: 'Mobile', price: 499, image: 'smartphone.jpg', specs: '128GB, 6GB RAM, 6.5" Display' },
        { id: 2, name: 'Laptop ABC', category: 'Laptop', price: 799, image: 'laptop.jpg', specs: '16GB RAM, 512GB SSD, 15.6" Display' },
        { id: 3, name: 'Wireless Headphones', category: 'Accessories', price: 99, image: 'headphones.jpg', specs: 'Noise Cancellation, Bluetooth 5.0' },
        // Add more products as needed
    ];

    const productContainer = document.getElementById('product-container');
    const categoryFilter = document.getElementById('category-filter');
    const sortSelect = document.getElementById('sort-select');
    const searchInput = document.getElementById('search-input');

    function renderProducts(products) {
        productContainer.innerHTML = '';
        products.forEach(product => {
            const productDiv = document.createElement('div');
            productDiv.className = 'product';
            productDiv.innerHTML = `
                <img src="${product.image}" alt="${product.name}">
                <h3>${product.name}</h3>
                <p>${product.specs}</p>
                <p>Price: $${product.price}</p>
            `;
            productContainer.appendChild(productDiv);
        });
    }

    function filterProducts(category) {
        return category === 'all' ? products : products.filter(product => product.category.toLowerCase() === category.toLowerCase());
    }

    function sortProducts(products, sortBy) {
        return products.sort((a, b) => {
            if (sortBy === 'price-asc') {
                return a.price - b.price;
            } else if (sortBy === 'price-desc') {
                return b.price - a.price;
            } else {
                return 0;
            }
        });
    }

    function searchProducts(query) {
        return products.filter(product => product.name.toLowerCase().includes(query.toLowerCase()));
    }

    function updateProducts() {
        const category = categoryFilter.value;
        const sortBy = sortSelect.value;
        const query = searchInput.value;

        let filteredProducts = filterProducts(category);
        filteredProducts = sortProducts(filteredProducts, sortBy);
        filteredProducts = searchProducts(query);

        renderProducts(filteredProducts);
    }

    categoryFilter.addEventListener('change', updateProducts);
    sortSelect.addEventListener('change', updateProducts);
    searchInput.addEventListener('input', updateProducts);

    // Initial render
    renderProducts(products);
});