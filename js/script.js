function addToCart(item, quantity, size) {
    fetch("http://127.0.0.1:5000/add_to_cart", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ item: item, quantity: quantity, size: size })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    })
    .catch(error => {
        console.error("Error adding item to cart:", error);
    });
}
function submitContactForm() {
    const formData = {
        name: document.getElementById('name').value,
        email: document.getElementById('email').value,
        phone: document.getElementById('phone').value,
        message: document.getElementById('message').value
    };

    console.log("Form Data:", formData); // Log form data

    fetch("http://127.0.0.1:5000/api/contact", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(formData)
    })
    .then(response => {
        console.log("Response Status:", response.status); // Log response status
        return response.json();
    })
    .then(data => {
        console.log("Response Data:", data); // Log response data
    })
    .catch(error => {
        console.error("Error:", error);
    });
}

