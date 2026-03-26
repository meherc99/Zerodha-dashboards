"""
Routes package.
"""
from app.routes.health import health_bp
from app.routes.accounts import accounts_bp
from app.routes.holdings import holdings_bp
from app.routes.analytics import analytics_bp
from app.routes.auth import auth_bp
from app.routes.categories import categories_bp

__all__ = [
    'health_bp',
    'accounts_bp',
    'holdings_bp',
    'analytics_bp',
    'auth_bp',
    'categories_bp'
]
