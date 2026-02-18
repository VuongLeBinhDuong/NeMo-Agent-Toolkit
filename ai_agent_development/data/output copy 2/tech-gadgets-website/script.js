// script.js for tech-gadgets-website

document.addEventListener('DOMContentLoaded', () => {
    const cartItems = JSON.parse(localStorage.getItem('cartItems')) || [];
    updateCartDisplay(cartItems);

    // Function to update cart display
    function updateCartDisplay(items) {
        const itemCount = items.reduce((total, item) => total + item.quantity, 0);
        const subtotal = items.reduce((total, item) => total + (item.price * item.quantity), 0).toFixed(2);

        document.getElementById('item-count').textContent = itemCount;
        document.getElementById('subtotal').textContent = `$${subtotal}`;
    }

    // Function to add item to cart
    function addToCart(product) {
        const existingItemIndex = cartItems.findIndex(item => item.id === product.id);
        if (existingItemIndex !== -1) {
            cartItems[existingItemIndex].quantity += 1;
        } else {
            cartItems.push({ ...product, quantity: 1 });
        }
        localStorage.setItem('cartItems', JSON.stringify(cartItems));
        updateCartDisplay(cartItems);
    }

    // Function to update item quantity in cart
    function updateCartItemQuantity(productId, quantity) {
        const itemIndex = cartItems.findIndex(item => item.id === productId);
        if (itemIndex !== -1) {
            cartItems[itemIndex].quantity = quantity;
            if (quantity <= 0) {
                cartItems.splice(itemIndex, 1);
            }
            localStorage.setItem('cartItems', JSON.stringify(cartItems));
            updateCartDisplay(cartItems);
        }
    }

    // Event listener for adding items to cart
    document.querySelectorAll('.add-to-cart').forEach(button => {
        button.addEventListener('click', () => {
            const product = {
                id: button.dataset.productId,
                name: button.dataset.productName,
                price: parseFloat(button.dataset.productPrice)
            };
            addToCart(product);
        });
    });

    // Event listener for updating item quantity in cart
    document.querySelectorAll('.cart-item-quantity').forEach(input => {
        input.addEventListener('change', (event) => {
            const productId = event.target.dataset.productId;
            const quantity = parseInt(event.target.value, 10);
            updateCartItemQuantity(productId, quantity);
        });
    });
});