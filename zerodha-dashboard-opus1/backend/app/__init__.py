"""
Flask application factory.
"""
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from app.config import config
from app.database import init_db, db
from app.services.scheduler_service import SchedulerService
import logging
import os


def create_app(config_name=None):
    """
    Create and configure Flask application.

    Args:
        config_name: Configuration name ('development', 'production', or None for default)

    Returns:
        Flask app instance
    """
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app.config.from_object(config[config_name])

    # Configure logging
    logging.basicConfig(
        level=logging.INFO if not app.debug else logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize extensions
    CORS(app, origins=app.config['CORS_ORIGINS'])
    jwt = JWTManager(app)

    # Initialize database
    init_db(app)

    # Register blueprints
    from app.routes import health_bp, accounts_bp, holdings_bp, analytics_bp, auth_bp

    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(accounts_bp)
    app.register_blueprint(holdings_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(auth_bp)

    # Initialize scheduler
    scheduler = SchedulerService()
    scheduler.init_app(app)
    app.scheduler = scheduler  # Store reference for access in routes

    @app.route('/')
    def index():
        """Root endpoint"""
        return {
            'service': 'Zerodha Portfolio Dashboard API',
            'version': '1.0.0',
            'status': 'running'
        }

    logging.info(f"Flask app created with config: {config_name}")

    return app
