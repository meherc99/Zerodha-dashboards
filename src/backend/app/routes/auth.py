"""User and Zerodha authentication endpoints."""
from datetime import datetime
import logging

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from kiteconnect import KiteConnect
from sqlalchemy.exc import IntegrityError

from app.database import db
from app.models.user import User
from app.models.revoked_token import RevokedToken
from app.utils.rate_limiter import rate_limit

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
REGISTER_FIELDS = {'email', 'password', 'full_name'}
LOGIN_FIELDS = {'email', 'password'}


@auth_bp.route('/register', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=60)  # 5 registrations per hour per IP
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
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    unexpected = sorted(set(data) - REGISTER_FIELDS)
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400

    raw_email = data.get('email')
    password = data.get('password', '')
    raw_full_name = data.get('full_name')

    if not isinstance(raw_email, str) or not raw_email.strip():
        return jsonify({'error': 'Email is required'}), 400
    email = raw_email.strip().lower()

    local_part, separator, domain = email.partition('@')
    if (
        len(email) > 255
        or not separator
        or not local_part
        or not domain
        or '@' in domain
    ):
        return jsonify({'error': 'Enter a valid email address'}), 400

    if not isinstance(password, str) or not password:
        return jsonify({'error': 'Password is required'}), 400

    if len(password) < 8 or len(password) > 1024:
        return jsonify({
            'error': 'Password must be between 8 and 1024 characters'
        }), 400

    if raw_full_name is None or raw_full_name == '':
        full_name = None
    elif not isinstance(raw_full_name, str):
        return jsonify({'error': 'full_name must be text'}), 400
    else:
        full_name = raw_full_name.strip()
        if not full_name or len(full_name) > 255:
            return jsonify({
                'error': 'full_name must be between 1 and 255 characters'
            }), 400

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

        logger.info("New user registered with ID %s", user.id)

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Email already exists'}), 409
    except Exception:
        db.session.rollback()
        logger.error("Unexpected error while registering user")
        return jsonify({'error': 'Failed to create user'}), 500


@auth_bp.route('/login', methods=['POST'])
@rate_limit(max_requests=10, window_minutes=15)  # 10 login attempts per 15 minutes per IP
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
    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    unexpected = sorted(set(data) - LOGIN_FIELDS)
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400

    raw_email = data.get('email')
    password = data.get('password', '')

    if not isinstance(raw_email, str) or not raw_email.strip():
        return jsonify({'error': 'Email is required'}), 400
    email = raw_email.strip().lower()

    if not isinstance(password, str) or not password:
        return jsonify({'error': 'Password is required'}), 400
    if len(password) > 1024:
        return jsonify({'error': 'Invalid email or password'}), 401

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

        logger.info("User %s logged in", user.id)

        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        }), 200

    except Exception:
        db.session.rollback()
        logger.error("Unexpected error during login")
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
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid authentication identity'}), 401

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict()), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Revoke the presented access token before the client discards it."""
    token = get_jwt()
    try:
        expires_at = datetime.utcfromtimestamp(int(token['exp']))
        user_id = int(get_jwt_identity())
        RevokedToken.query.filter(
            RevokedToken.expires_at <= datetime.utcnow()
        ).delete(synchronize_session=False)
        db.session.add(
            RevokedToken(
                jti=token['jti'],
                user_id=user_id,
                expires_at=expires_at,
            )
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    except (KeyError, TypeError, ValueError):
        db.session.rollback()
        return jsonify({'error': 'Invalid authentication token'}), 401
    except Exception:
        db.session.rollback()
        logger.error("Failed to revoke authentication token")
        return jsonify({'error': 'Logout failed'}), 500

    return jsonify({'message': 'Successfully logged out'}), 200

@auth_bp.route('/login-url', methods=['POST'])
@jwt_required()
def get_login_url():
    """Return the Zerodha login URL for a given API key."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON data'}), 400
    unexpected = sorted(set(data) - {'api_key'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400
    api_key = data.get('api_key')

    if (
        not isinstance(api_key, str)
        or not 10 <= len(api_key.strip()) <= 255
    ):
        return jsonify({'error': 'Enter a valid api_key'}), 400

    try:
        login_url = KiteConnect(api_key=api_key.strip()).login_url()
        return jsonify({'login_url': login_url}), 200
    except Exception:
        logger.error("Failed to build Kite login URL")
        return jsonify({'error': 'Failed to generate login URL'}), 500


@auth_bp.route('/access-token', methods=['POST'])
@jwt_required()
def exchange_access_token():
    """Do not expose brokerage tokens to the browser."""
    return jsonify({
        'error': 'This endpoint no longer returns brokerage tokens',
        'message': (
            'Send request_token to POST /api/accounts or PUT /api/accounts/:id; '
            'the server will exchange and encrypt it directly.'
        ),
    }), 410
