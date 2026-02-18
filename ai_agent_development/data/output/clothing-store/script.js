document.addEventListener('DOMContentLoaded', () => {
    const products = [
        { name: "Men's T-Shirt", price: 15.99, category: "Men", description: "A high-quality men's t-shirt made from cotton." },
        { name: "Women's Dress", price: 29.99, category: "Women", description: "A stylish women's dress perfect for any occasion." },
        { name: "Kids' Sneakers", price: 19.99, category: "Kids", description: "A pair of comfortable kids' sneakers for everyday wear." },
        { name: "Men's Jacket", price: 49.99, category: "Men", description: "A warm and durable men's jacket for the winter season." },
        { name: "Women's Boots", price: 39.99, category: "Women", description: "A pair of stylish women's boots for the fall season." },
        { name: "Kids' Hoodie", price: 14.99, category: "Kids", description: "A cozy kids' hoodie for casual wear." }
    ];

    const searchInput = document.getElementById('search-input');
    const categoryFilter = document.getElementById('category-filter');
    const sortSelect = document.getElementById('sort-select');
    const cartCount = document.getElementById('cart-count');
    const cartSubtotal = document.getElementById('cart-subtotal');
    const productCards = document.querySelectorAll('.product-card');
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');

    let cart = [];
    let displayedProducts = [...products];

    function updateProductDisplay(filteredProducts) {
        productCards.forEach((card, index) => {
            if (index < filteredProducts.length) {
                card.querySelector('h3').textContent = filteredProducts[index].name;
                card.querySelector('p').textContent = `$${filteredProducts[index].price.toFixed(2)}`;
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    }

    function filterProducts() {
        const searchTerm = searchInput.value.toLowerCase();
        const selectedCategory = categoryFilter.value;
        let filteredProducts = products.filter(product => 
            product.name.toLowerCase().includes(searchTerm) && 
            (selectedCategory === 'All' || product.category === selectedCategory)
        );

        const sortOption = sortSelect.value;
        switch (sortOption) {
            case 'Price (asc)':
                filteredProducts.sort((a, b) => a.price - b.price);
                break;
            case 'Price (desc)':
                filteredProducts.sort((a, b) => b.price - a.price);
                break;
            default:
                break;
        }

        displayedProducts = filteredProducts;
        updateProductDisplay(filteredProducts);
    }

    function addToCart(event) {
        const productName = event.target.getAttribute('data-product-name');
        const product = products.find(p => p.name === productName);
        if (product) {
            cart.push(product);
            updateCart();
        }
    }

    function updateCart() {
        cartCount.textContent = cart.length;
        const subtotal = cart.reduce((total, product) => total + product.price, 0);
        cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
    }

    searchInput.addEventListener('input', filterProducts);
    categoryFilter.addEventListener('change', filterProducts);
    sortSelect.addEventListener('change', filterProducts);
    addToCartButtons.forEach(button => button.addEventListener('click', addToCart));

    updateProductDisplay(products);
});