"""
Rate limiting utilities using in-memory storage.

For production, consider using Redis-backed rate limiting with Flask-Limiter.
"""
from functools import wraps
from flask import request, jsonify
from datetime import datetime, timedelta
from collections import defaultdict
import threading

# In-memory storage for rate limiting
# Format: {key: {'count': int, 'reset_time': datetime}}
_rate_limit_storage = defaultdict(dict)
_storage_lock = threading.Lock()


def rate_limit(max_requests=10, window_minutes=60, key_func=None):
    """
    Rate limiting decorator.

    Args:
        max_requests: Maximum number of requests allowed
        window_minutes: Time window in minutes
        key_func: Function to generate rate limit key (default: uses IP address)

    Returns:
        Decorated function that enforces rate limiting

    Example:
        @rate_limit(max_requests=5, window_minutes=60)
        def my_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate key for this request
            if key_func:
                key = key_func()
            else:
                # Default: use IP address
                key = f"ratelimit:{f.__name__}:{request.remote_addr}"

            with _storage_lock:
                now = datetime.utcnow()

                # Get or create rate limit data
                if key not in _rate_limit_storage:
                    _rate_limit_storage[key] = {
                        'count': 0,
                        'reset_time': now + timedelta(minutes=window_minutes)
                    }

                data = _rate_limit_storage[key]

                # Check if window has expired
                if now >= data['reset_time']:
                    # Reset counter
                    data['count'] = 0
                    data['reset_time'] = now + timedelta(minutes=window_minutes)

                # Increment counter
                data['count'] += 1

                # Check if limit exceeded
                if data['count'] > max_requests:
                    retry_after = int((data['reset_time'] - now).total_seconds())
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'retry_after': retry_after
                    }), 429

            # Call the original function
            return f(*args, **kwargs)

        return decorated_function
    return decorator


def user_rate_limit(max_requests=10, window_minutes=60):
    """
    Rate limiting decorator that uses authenticated user ID as key.

    Args:
        max_requests: Maximum number of requests allowed
        window_minutes: Time window in minutes

    Returns:
        Decorated function that enforces rate limiting per user

    Example:
        @jwt_required()
        @user_rate_limit(max_requests=10, window_minutes=60)
        def my_route():
            ...
    """
    def key_func():
        from flask_jwt_extended import get_jwt_identity
        try:
            user_id = get_jwt_identity()
            from flask import current_app
            route_name = request.endpoint or 'unknown'
            return f"ratelimit:user:{user_id}:{route_name}"
        except:
            # Fallback to IP if JWT not available
            return f"ratelimit:ip:{request.remote_addr}:{request.endpoint}"

    return rate_limit(max_requests=max_requests, window_minutes=window_minutes, key_func=key_func)


def cleanup_expired_entries():
    """
    Clean up expired rate limit entries from storage.

    Should be called periodically to prevent memory leaks.
    """
    with _storage_lock:
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in _rate_limit_storage.items()
            if now >= data.get('reset_time', now)
        ]

        for key in expired_keys:
            del _rate_limit_storage[key]

        return len(expired_keys)
