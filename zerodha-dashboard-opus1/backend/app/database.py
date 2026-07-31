"""
Database initialization and session management.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

# Initialize SQLAlchemy instance
db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)

    with app.app_context():
        if db.engine.dialect.name == 'sqlite':
            @event.listens_for(db.engine, 'connect')
            def enable_sqlite_foreign_keys(connection, _record):
                cursor = connection.cursor()
                cursor.execute('PRAGMA foreign_keys=ON')
                cursor.close()

        # Import models to register them with SQLAlchemy
        from app.models import account, holding, snapshot, historical_price, user
