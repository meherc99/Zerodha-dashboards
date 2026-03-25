"""
Database initialization and session management.
"""
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy instance
db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)

    with app.app_context():
        # Import models to register them with SQLAlchemy
        from app.models import account, holding, snapshot, historical_price, user

        print("Database initialized successfully!")
