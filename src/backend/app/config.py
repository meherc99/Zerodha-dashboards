"""
Configuration module for Zerodha Dashboard application.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration"""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_BYTES', 10 * 1024 * 1024))

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///zerodha_dashboard.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')

    # Scheduler
    SCHEDULER_API_ENABLED = True
    SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'false').lower() in {
        '1', 'true', 'yes'
    }
    SCHEDULER_TIMEZONE = "Asia/Kolkata"
    SYNC_INTERVAL_HOURS = int(os.environ.get('SYNC_INTERVAL_HOURS', 12))

    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

    # Zerodha API
    KITE_API_TIMEOUT = int(os.environ.get('KITE_API_TIMEOUT', 30))
    KITE_RETRY_ATTEMPTS = int(os.environ.get('KITE_RETRY_ATTEMPTS', 3))

    # Rate Limiting
    RATELIMIT_ENABLED = os.environ.get(
        'RATELIMIT_ENABLED',
        'true',
    ).lower() in {'1', 'true', 'yes'}
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE = os.environ.get('RATELIMIT_STORAGE', 'memory').lower()

    # JWT Authentication
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True for SQL query logging


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}
