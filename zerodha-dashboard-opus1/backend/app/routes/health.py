"""
Health check endpoint.
"""
from flask import Blueprint, jsonify
from app.database import db
import time

health_bp = Blueprint('health', __name__)

_start_time = time.time()


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    uptime = time.time() - _start_time

    return jsonify({
        'status': 'ok' if db_status == 'connected' else 'degraded',
        'service': 'zerodha-dashboard',
        'database': db_status,
        'uptime_seconds': round(uptime, 2)
    }), 200
