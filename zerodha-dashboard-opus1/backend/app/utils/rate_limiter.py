"""Fixed-window request limiting with shared production persistence."""
import hashlib
import logging
from functools import wraps
from flask import current_app, request, jsonify
from datetime import datetime, timedelta
import threading
from sqlalchemy.exc import IntegrityError


logger = logging.getLogger(__name__)

# In-memory storage for rate limiting
# Format: {key: {'count': int, 'reset_time': datetime}}
_rate_limit_storage = {}
_storage_lock = threading.Lock()
_MAX_RATE_LIMIT_KEYS = 10_000


def _consume_memory_bucket(key, window_minutes):
    """Increment one bounded process-local development/test bucket."""
    with _storage_lock:
        now = datetime.utcnow()
        if key not in _rate_limit_storage:
            if len(_rate_limit_storage) >= _MAX_RATE_LIMIT_KEYS:
                expired_keys = [
                    existing_key
                    for existing_key, existing_data
                    in _rate_limit_storage.items()
                    if now >= existing_data['reset_time']
                ]
                for expired_key in expired_keys:
                    del _rate_limit_storage[expired_key]
            if len(_rate_limit_storage) >= _MAX_RATE_LIMIT_KEYS:
                del _rate_limit_storage[next(iter(_rate_limit_storage))]
            _rate_limit_storage[key] = {
                'count': 0,
                'reset_time': now + timedelta(minutes=window_minutes),
            }

        data = _rate_limit_storage[key]
        if now >= data['reset_time']:
            data['count'] = 0
            data['reset_time'] = now + timedelta(minutes=window_minutes)
        data['count'] += 1
        return data['count'], data['reset_time'], now


def _consume_database_bucket(key, window_minutes):
    """Atomically increment a shared SQL bucket across app workers."""
    from app.database import db
    from app.models.rate_limit_bucket import RateLimitBucket

    key_hash = hashlib.sha256(key.encode()).hexdigest()
    for _attempt in range(5):
        now = datetime.utcnow()
        try:
            updated = (
                RateLimitBucket.query.filter(
                    RateLimitBucket.key_hash == key_hash,
                    RateLimitBucket.reset_time > now,
                )
                .update(
                    {'count': RateLimitBucket.count + 1},
                    synchronize_session=False,
                )
            )
            if updated:
                bucket = db.session.get(RateLimitBucket, key_hash)
                count = bucket.count
                reset_time = bucket.reset_time
                db.session.commit()
                return count, reset_time, now

            RateLimitBucket.query.filter(
                RateLimitBucket.reset_time <= now
            ).delete(synchronize_session=False)
            reset_time = now + timedelta(minutes=window_minutes)
            db.session.add(
                RateLimitBucket(
                    key_hash=key_hash,
                    count=1,
                    reset_time=reset_time,
                )
            )
            db.session.commit()
            return 1, reset_time, now
        except IntegrityError:
            # A competing worker created/reset this key; retry its live row.
            db.session.rollback()
    raise RuntimeError('Unable to update shared rate-limit counter')


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
            if not current_app.config.get('RATELIMIT_ENABLED', True):
                return f(*args, **kwargs)

            # Generate key for this request
            if key_func:
                key = str(key_func())
            else:
                # Default: use IP address
                client_address = request.remote_addr or 'unknown'
                route_name = request.endpoint or f.__name__
                key = f"ratelimit:{route_name}:{client_address}"

            try:
                storage = current_app.config.get(
                    'RATELIMIT_STORAGE',
                    'memory',
                )
                if storage == 'database':
                    count, reset_time, now = _consume_database_bucket(
                        key,
                        window_minutes,
                    )
                elif storage == 'memory':
                    count, reset_time, now = _consume_memory_bucket(
                        key,
                        window_minutes,
                    )
                else:
                    raise RuntimeError('Unsupported rate-limit storage')
            except Exception:
                logger.error("Rate-limit storage is unavailable")
                return jsonify({
                    'error': 'Request protection is temporarily unavailable'
                }), 503

            if count > max_requests:
                retry_after = max(
                    1,
                    int((reset_time - now).total_seconds()),
                )
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'retry_after': retry_after
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(retry_after)
                return response

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
        user_id = get_jwt_identity()
        route_name = request.endpoint or 'unknown'
        if user_id is not None:
            return f"ratelimit:user:{user_id}:{route_name}"
        client_address = request.remote_addr or 'unknown'
        return f"ratelimit:ip:{client_address}:{route_name}"

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
