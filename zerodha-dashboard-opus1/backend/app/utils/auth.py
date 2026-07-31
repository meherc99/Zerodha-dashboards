"""Authentication and ownership helpers shared by portfolio routes."""
from flask import abort, g, jsonify
from flask_jwt_extended import get_jwt_identity

from app.database import db
from app.models.account import Account
from app.models.user import User


def current_user_id():
    """Return the numeric user ID carried by a verified JWT.

    Tokens created by this application always use a string subject.  Invalid
    subjects are rejected as authentication failures instead of becoming 500s.
    """
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        user_id = 0

    if user_id <= 0:
        response = jsonify({'error': 'Invalid authentication identity'})
        response.status_code = 401
        abort(response)

    # ``g`` normally lives for one request, but tests, scripts, and some job
    # runners may preserve an outer app context across requests. Never reuse a
    # cached tenant unless it matches the currently verified JWT subject.
    if getattr(g, 'portfolio_user_id', None) == user_id:
        return user_id

    user = db.session.get(User, user_id)
    if user is None or not user.is_active:
        response = jsonify({'error': 'User account is unavailable'})
        response.status_code = 401
        abort(response)

    g.portfolio_user_id = user_id
    return user_id


def owned_account(account_id, user_id=None, active_only=False):
    """Return an account only when it belongs to the authenticated user."""
    user_id = user_id or current_user_id()
    query = Account.query.filter_by(id=account_id, user_id=user_id)
    if active_only:
        query = query.filter_by(is_active=True)
    return query.first()
