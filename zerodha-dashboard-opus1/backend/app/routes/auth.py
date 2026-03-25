"""
Authentication endpoints for user registration, login, and profile management.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.database import db
from app.models.user import User
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
        {
            "email": "user@example.com",
            "password": "secure_password",
            "full_name": "User Name" (optional)
        }

    Returns:
        201: {"access_token": "...", "user": {...}}
        400: {"error": "error message"}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    # Validate required fields
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip() if data.get('full_name') else None

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    if not password:
        return jsonify({'error': 'Password is required'}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'Email already exists'}), 400

    # Create new user
    user = User(email=email, full_name=full_name)
    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()

        # Generate JWT token (identity must be a string)
        access_token = create_access_token(identity=str(user.id))

        logger.info(f"New user registered: {email}")

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({'error': 'Failed to create user'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token.

    Request body:
        {
            "email": "user@example.com",
            "password": "secure_password"
        }

    Returns:
        200: {"access_token": "...", "user": {...}}
        400: {"error": "error message"}
        401: {"error": "error message"}
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    # Validate required fields
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    if not password:
        return jsonify({'error': 'Password is required'}), 400

    # Find user
    user = User.query.filter_by(email=email).first()

    # Verify user exists and password is correct
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check if user is active
    if not user.is_active:
        return jsonify({'error': 'Account is inactive'}), 401

    # Update last login timestamp
    user.last_login_at = datetime.utcnow()

    try:
        db.session.commit()

        # Generate JWT token (identity must be a string)
        access_token = create_access_token(identity=str(user.id))

        logger.info(f"User logged in: {email}")

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during login: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user profile.

    Requires: JWT token in Authorization header

    Returns:
        200: User profile object
        401: Unauthorized (no token or invalid token)
    """
    user_id = int(get_jwt_identity())  # Convert back to int from string
    user = User.query.get(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict()), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout endpoint (client-side token deletion).

    Note: JWT tokens are stateless. Actual logout is handled client-side
    by deleting the token. This endpoint exists for consistency and
    future token blacklisting implementation.

    Returns:
        200: {"message": "Successfully logged out"}
        401: Unauthorized if JWT token is missing or invalid
    """
    return jsonify({'message': 'Successfully logged out'}), 200
