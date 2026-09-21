"""Flask application factory."""
import logging
import os
from collections.abc import Mapping

from flask import Flask, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from cryptography.fernet import Fernet
from werkzeug.exceptions import RequestEntityTooLarge

from app.config import config
from app.database import db, init_db
from app.services.scheduler_service import SchedulerService


def create_app(config_overrides=None):
    """Create an application without starting background worker threads.

    ``config_overrides`` may be a configuration name (``development`` or
    ``production``) or a mapping.  Mapping values are applied before any
    extension is initialized so tests can reliably select an isolated database.
    """
    app = Flask(__name__)

    configured_environment = os.environ.get("FLASK_ENV")
    if isinstance(config_overrides, str):
        config_name = config_overrides
        config_overrides = None
    elif isinstance(config_overrides, Mapping):
        # A mapping is an explicit programmatic configuration (primarily tests).
        config_name = configured_environment or "development"
    else:
        # A deployment that forgets to select an environment must fail closed
        # through production validation, never start with development secrets.
        config_name = configured_environment or "production"

    if config_name not in config:
        raise RuntimeError(
            f"Unsupported FLASK_ENV {config_name!r}; use development or production"
        )

    app.config.from_object(config[config_name])
    if isinstance(config_overrides, Mapping):
        app.config.update(config_overrides)
    elif config_overrides is not None:
        raise TypeError("config_overrides must be a config name or mapping")

    configured_origins = app.config.get("CORS_ORIGINS", [])
    if isinstance(configured_origins, str):
        configured_origins = configured_origins.split(",")
    cors_origins = [
        origin.strip()
        for origin in configured_origins
        if isinstance(origin, str) and origin.strip()
    ]
    app.config["CORS_ORIGINS"] = cors_origins

    if config_name == "production":
        insecure_values = {
            None,
            "",
            "dev-secret-key-change-in-production",
            "your-secret-key-change-in-production",
        }
        secret_key = app.config.get("SECRET_KEY")
        jwt_secret_key = app.config.get("JWT_SECRET_KEY")
        if (
            secret_key in insecure_values
            or jwt_secret_key in insecure_values
            or not isinstance(secret_key, (str, bytes))
            or not isinstance(jwt_secret_key, (str, bytes))
            or len(secret_key) < 32
            or len(jwt_secret_key) < 32
            or secret_key == jwt_secret_key
        ):
            raise RuntimeError(
                "Set distinct SECRET_KEY and JWT_SECRET_KEY values of at "
                "least 32 bytes in production"
            )
        encryption_key = app.config.get("ENCRYPTION_KEY")
        try:
            Fernet(
                encryption_key.encode()
                if isinstance(encryption_key, str)
                else encryption_key
            )
        except (TypeError, ValueError):
            raise RuntimeError(
                "Set ENCRYPTION_KEY to a valid Fernet key in production"
            ) from None
        if not cors_origins or "*" in cors_origins:
            raise RuntimeError(
                "Set CORS_ORIGINS to explicit trusted origins in production"
            )
        if app.config.get("RATELIMIT_STORAGE") != "database":
            raise RuntimeError(
                "Set RATELIMIT_STORAGE=database in production so limits are "
                "shared across workers and restarts"
            )

    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Reconcile files written by older releases before the application accepts
    # requests. Unsafe links or special files stop startup instead of being
    # followed through a privileged application process.
    from app.services.bank_statement_service import BankStatementService
    BankStatementService.harden_upload_permissions()

    CORS(
        app,
        origins=app.config["CORS_ORIGINS"],
        supports_credentials=False,
        allow_headers=["Authorization", "Content-Type"],
    )
    jwt = JWTManager(app)
    init_db(app)

    from app.models.revoked_token import RevokedToken
    from app.models.user import User

    @jwt.token_in_blocklist_loader
    def is_token_revoked(_jwt_header, jwt_data):
        jti = jwt_data.get("jti")
        if not isinstance(jti, str):
            return True
        return (
            db.session.query(RevokedToken.id)
            .filter(RevokedToken.jti == jti)
            .first()
            is not None
        )

    @jwt.revoked_token_loader
    def revoked_jwt(_jwt_header, _jwt_data):
        return {"error": "Authentication token has been revoked"}, 401

    @jwt.user_lookup_loader
    def load_jwt_user(_jwt_header, jwt_data):
        try:
            user_id = int(jwt_data.get("sub"))
        except (TypeError, ValueError):
            return None
        user = db.session.get(User, user_id)
        return user if user is not None and user.is_active else None

    @jwt.user_lookup_error_loader
    def missing_jwt_user(_jwt_header, _jwt_data):
        return {"error": "User account is unavailable"}, 401

    from app.routes import (
        accounts_bp,
        analytics_bp,
        auth_bp,
        categories_bp,
        health_bp,
        holdings_bp,
    )
    from app.routes.bank_accounts import bank_accounts_bp
    from app.routes.bank_analytics import bank_analytics_bp
    from app.routes.bank_statements import bank_statements_bp
    from app.routes.transactions import transactions_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(holdings_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(bank_accounts_bp)
    app.register_blueprint(bank_statements_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(transactions_bp, url_prefix="/api")
    app.register_blueprint(bank_analytics_bp, url_prefix="/api")

    # The scheduler is available to manual-sync routes but is started only by
    # the executable entry point.  App factories, migrations, and tests stay
    # deterministic and do not leak background threads.
    app.scheduler = SchedulerService(app)

    @app.errorhandler(RequestEntityTooLarge)
    def upload_too_large(_error):
        # Upload endpoints consistently expose validation failures as 400s.
        return {"error": "File size exceeds the maximum allowed size"}, 400

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), geolocation=(), microphone=()",
        )
        if request.path.startswith("/api/"):
            response.headers.setdefault(
                "Cache-Control",
                "no-store, max-age=0",
            )
            response.headers.setdefault("Pragma", "no-cache")
        if config_name == "production" and request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response

    @app.get("/")
    def index():
        return {
            "service": "Zerodha Portfolio Dashboard API",
            "version": "1.0.0",
            "status": "running",
        }

    app.logger.info("Flask app created with config: %s", config_name)
    return app


__all__ = ["create_app", "db"]
