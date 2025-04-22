from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import functools
from bson.objectid import ObjectId
from bson import ObjectId

# Initialize Flask App
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication
app.secret_key = "your_secret_key_here"  # Change this to a secure secret key
app.permanent_session_lifetime = timedelta(days=7)  # Set session lifetime

# MongoDB Connection
app.config["MONGO_URI"] = "mongodb+srv://root123:12345@cluster0.jgaak.mongodb.net/fruitopia"
mongo = PyMongo(app)

# Ensure collections exist
db = mongo.db
if "fruits" not in db.list_collection_names():
    db.create_collection("fruits")
if "contacts" not in db.list_collection_names():
    db.create_collection("contacts")
if "users" not in db.list_collection_names():
    db.create_collection("users")
if "cart" not in db.list_collection_names():
    db.create_collection("cart")

# Fruit Prices (if not stored in DB)
FRUIT_PRICES = {
    "Orange": 60,
    "Grapes": 85,
    "Guava": 65,
    "Apple": 90,
    "Banana": 40,
    "Kiwi": 170,
}

# Login required decorator
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Add this to ensure session works properly
@app.before_request
def session_handling():
    session.permanent = True

# ---------------------- Routes ---------------------- #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/fruits')
def fruits():
    return render_template('fruit.html')

@app.route('/services')
def services():
    return render_template('service.html')

# ---------------------- Cart Routes ---------------------- #

@app.route('/cart')
@login_required
def cart():
    """Fetches cart items from MongoDB and renders the cart page."""
    try:
        cart_items = list(mongo.db.cart.find(
            {'user_id': session['user']['id']}, 
            {'_id': 0}
        ))
        total_price = sum(item.get('total', 0) for item in cart_items)
        return render_template('cart.html', cart_items=cart_items, total_price=total_price)
    except Exception as e:
        print(f"Error: {str(e)}")
        return render_template('cart.html', cart_items=[], total_price=0)

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    """Adds an item to the cart or updates quantity if it already exists."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data received"}), 400

        cart_item = {
            "user_id": session['user']['id'],  # Add user ID to cart item
            "fruit": data.get('fruit'),
            "quantity": int(data.get('quantity', 1)),
            "weight": data.get('weight'),
            "price": FRUIT_PRICES.get(data.get('fruit'), 0)
        }
        
        cart_item['total'] = cart_item['price'] * cart_item['quantity']
        
        mongo.db.cart.insert_one(cart_item)
        
        return jsonify({
            "success": True,
            "message": "Added to cart successfully",
            "redirect": "/cart"
        })

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/cart_items', methods=['GET'])
def get_cart_items():
    """Fetches all cart items and total price."""
    try:
        cart_items = list(mongo.db.cart.find({}, {'_id': 0}))
        total_price = sum(item.get('total', 0) for item in cart_items)
        return jsonify(cart_items=cart_items, total_price=total_price)
    except Exception as e:
        print(f"Error fetching cart items: {str(e)}")
        return jsonify({"error": "Failed to fetch cart items"}), 500

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    """Removes an item from the cart."""
    try:
        data = request.get_json()
        fruit_name = data.get("fruit")

        if not fruit_name:
            return jsonify({"error": "No fruit specified"}), 400

        mongo.db.cart.delete_one({"fruit": fruit_name})
        return jsonify({"success": True, "message": "Item removed from cart"}), 200

    except Exception as e:
        print(f"Error in remove_from_cart: {str(e)}")
        return jsonify({"error": "Failed to remove item"}), 500

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    """Clears all items from the cart."""
    try:
        mongo.db.cart.delete_many({})
        return jsonify({"success": True, "message": "Cart cleared successfully"}), 200
    except Exception as e:
        print(f"Error in clear_cart: {str(e)}")
        return jsonify({"error": "Failed to clear cart"}), 500

# ---------------------- API Routes ---------------------- #

@app.route('/fruit/<name>', methods=['GET'])
def get_fruit(name):
    """Fetches a fruit's details from MongoDB."""
    fruit = mongo.db.fruits.find_one({"name": name}, {"_id": 0})
    if fruit:
        return jsonify(fruit), 200
    else:
        return jsonify({"error": "Fruit not found"}), 404

@app.route('/api/contact', methods=['POST'])
def save_contact():
    """Saves contact form submission to MongoDB."""
    data = request.get_json()
    if not data or not all(k in data for k in ["name", "email", "message"]):
        return jsonify({"error": "Missing fields"}), 400

    try:
        mongo.db.contacts.insert_one(data)
        return jsonify({"success": True, "message": "Message received!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/payment')
def payment():
    try:
        cart_items = list(mongo.db.cart.find({}, {'_id': 0}))
        total_price = sum(item.get('total', 0) for item in cart_items)
        return render_template('payment.html', cart_items=cart_items, total_price=total_price)
    except Exception as e:
        print(f"Error in payment route: {str(e)}")
        return render_template('payment.html', cart_items=[], total_price=0)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    try:
        data = request.get_json()
        
        # Create order in database
        order = {
            'customer_name': data.get('fullName'),
            'address': data.get('address'),
            'city': data.get('city'),
            'pincode': data.get('pincode'),
            'payment_method': data.get('paymentMethod'),
            'cart_items': list(mongo.db.cart.find({}, {'_id': 0})),
            'total_amount': sum(item.get('total', 0) for item in mongo.db.cart.find({}, {'_id': 0})),
            'order_date': datetime.now(),
            'status': 'pending'
        }
        
        # Save order to MongoDB
        mongo.db.orders.insert_one(order)
        
        # Clear the cart after successful order
        mongo.db.cart.delete_many({})
        
        return jsonify({
            'success': True,
            'message': 'Order placed successfully!'
        })
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to process payment'
        }), 500

@app.route('/order_confirmation')
def order_confirmation():
    return render_template('order_confirmation.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = mongo.db.users.find_one({'email': email})
        
        if user and check_password_hash(user['password'], password):
            session['user'] = {
                'id': str(user['_id']),
                'name': user['name'],
                'email': user['email']
            }
            return redirect(url_for('index'))
        
        return render_template('login.html', error='Invalid email or password')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        if mongo.db.users.find_one({'email': email}):
            return render_template('register.html', error='Email already registered')
        
        hashed_password = generate_password_hash(password)
        
        user = {
            'name': name,
            'email': email,
            'password': hashed_password
        }
        
        mongo.db.users.insert_one(user)
        
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    # Print debug information
    print("Logout route accessed")
    print("Session before clearing:", session)
    
    # Clear the session
    session.pop('user', None)
    session.clear()
    
    print("Session after clearing:", session)
    
    # Redirect to home page
    return redirect(url_for('index'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Check if user exists
        user = mongo.db.users.find_one({'email': email})
        if user:
            # Here you would typically:
            # 1. Generate a reset token
            # 2. Send a reset email
            # 3. Save the token in the database
            return render_template('forgot_password.html', 
                                message='Password reset instructions sent to your email.')
        else:
            return render_template('forgot_password.html', 
                                error='No account found with that email.')
    
    return render_template('forgot_password.html')

@app.route('/profile')
@login_required
def profile():
    try:
        # Get user details from session
        user_id = session['user']['id']
        user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        
        # Get user's orders
        orders = list(mongo.db.orders.find({'user_id': user_id}))
        
        return render_template('profile.html', user=user, orders=orders)
    except Exception as e:
        print(f"Error in profile route: {str(e)}")
        return redirect(url_for('index'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    try:
        user_id = session['user']['id']
        
        # Get form data
        update_data = {
            'name': request.form.get('name'),
            'email': request.form.get('email'),
            'phone': request.form.get('phone'),
            'address': request.form.get('address')
        }
        
        # Update user in database
        mongo.db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_data}
        )
        
        # Update session
        session['user']['name'] = update_data['name']
        session['user']['email'] = update_data['email']
        
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ---------------------- Run Flask App ---------------------- #
if __name__ == "__main__":
    app.run(debug=True)