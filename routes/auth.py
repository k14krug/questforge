from flask import Blueprint, request, jsonify, render_template # Import render_template
from database import db # Import db directly from database
from models import User # Import User model
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity,
    set_access_cookies, unset_jwt_cookies # Import cookie functions
)
from datetime import datetime, timedelta
import uuid
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
user_bp = Blueprint('user', __name__, url_prefix='/api/users') # New blueprint for user management
bcrypt = Bcrypt()

# Helper for error responses
def error_response(message, status_code, details=None):
    response = {"error": message}
    if details:
        response["details"] = details
    return jsonify(response), status_code

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return error_response("Invalid JSON", 400)

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    errors = {}
    if not username:
        errors['username'] = 'Username is required.'
    elif len(username) < 3 or len(username) > 50:
        errors['username'] = 'Username must be between 3 and 50 characters.'

    if not email:
        errors['email'] = 'Email is required.'
    elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        errors['email'] = 'Invalid email format.'

    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters long.'
    # Add more password strength checks if needed (e.g., special chars, numbers)

    if errors:
        return error_response("Invalid input data", 400, errors)

    # Check for existing user
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        if existing_user.username == username:
            return error_response("User with this username already exists", 409, {"username": "Username already taken"})
        else:
            return error_response("User with this email already exists", 409, {"email": "Email already taken"})

    try:
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            created_at=datetime.utcnow()
        )
        db.session.add(new_user)
        db.session.commit()

        return jsonify({
            "message": "User registered successfully",
            "user_id": new_user.id
        }), 201

    except Exception as e:
        db.session.rollback()
        # Log the error (as per error_handling_guidelines.md)
        print(f"ERROR: Failed to register user: {e}") # Placeholder for actual logging
        return error_response("An unexpected error occurred during registration", 500)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return error_response("Invalid JSON", 400)

    username_or_email = data.get('username_or_email')
    password = data.get('password')

    if not username_or_email or not password:
        return error_response("Username/email and password are required", 400)

    user = User.query.filter(
        (User.username == username_or_email) | (User.email == username_or_email)
    ).first()

    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return error_response("Invalid credentials", 401)

    try:
        # Update last_login timestamp
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create access token
        access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(hours=1))
        response_data = {
            "message": "Login successful",
            "access_token": access_token, # Still returning token for JS if needed
            "token_type": "bearer"
        }
        response = jsonify(response_data)
        set_access_cookies(response, access_token)
        return response, 200

    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to log in user: {e}") # Placeholder for actual logging
        return error_response("An unexpected error occurred during login", 500)

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Flask-JWT-Extended handles token validation automatically via @jwt_required()
    # For a simple logout, we just return a success message.
    # If server-side token blacklisting/revocation is needed,
    # additional logic would be implemented here (e.g., adding token to a blacklist).
    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)
    return response, 200

@auth_bp.route('/login-page', methods=['GET'])
def login_page():
    return render_template('auth/login.html')

@auth_bp.route('/register-page', methods=['GET'])
def register_page():
    return render_template('auth/register.html')

# User Management Endpoints
@user_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_current_user_profile():
    """
    Gets the profile of the currently authenticated user.
    """
    current_user_id_str = get_jwt_identity()
    user = User.query.get(int(current_user_id_str))
    if not user:
        return error_response("User not found", 404)
    
    # Assuming User model has a to_dict() method that serializes it safely
    return jsonify(user.to_dict()), 200

@user_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_profile(user_id):
    current_user_id_str = get_jwt_identity()
    if current_user_id_str != str(user_id):
        return error_response("Access denied", 403)

    user = User.query.get(user_id)
    if not user:
        return error_response("User not found", 404)

    return jsonify(user.to_dict()), 200

@user_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user_profile(user_id):
    current_user_id_str = get_jwt_identity()
    if current_user_id_str != str(user_id):
        return error_response("Access denied", 403)

    user = User.query.get(user_id)
    if not user:
        return error_response("User not found", 404)

    data = request.get_json()
    if not data:
        return error_response("Invalid JSON", 400)

    errors = {}
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    character_backstories = data.get('character_backstories')

    if username:
        if len(username) < 3 or len(username) > 50:
            errors['username'] = 'Username must be between 3 and 50 characters.'
        elif User.query.filter(User.username == username, User.id != user_id).first():
            errors['username'] = 'Username already taken.'
        else:
            user.username = username

    if email:
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors['email'] = 'Invalid email format.'
        elif User.query.filter(User.email == email, User.id != user_id).first():
            errors['email'] = 'Email already taken.'
        else:
            user.email = email

    if password:
        if len(password) < 8:
            errors['password'] = 'Password must be at least 8 characters long.'
        else:
            user.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    if character_backstories is not None:
        if not isinstance(character_backstories, list):
            errors['character_backstories'] = 'Character backstories must be a list.'
        else:
            # Append new backstories to the existing list
            # Ensure the existing list is mutable if it's coming directly from JSON
            if user.character_backstories is None:
                user.character_backstories = []
            user.character_backstories.extend(character_backstories)

    if errors:
        return error_response("Invalid input data", 400, errors)

    try:
        db.session.commit()
        return jsonify({
            "message": "User profile updated successfully",
            "user_id": user.id
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"ERROR: Failed to update user profile: {e}")
        return error_response("An unexpected error occurred during profile update", 500)
