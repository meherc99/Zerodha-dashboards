"""Shared fixed-window counters for production rate limiting."""
from app.database import db


class RateLimitBucket(db.Model):
    """One hashed route/principal counter for a bounded time window."""

    __tablename__ = 'rate_limit_buckets'

    key_hash = db.Column(db.String(64), primary_key=True)
    count = db.Column(db.Integer, nullable=False)
    reset_time = db.Column(db.DateTime, nullable=False, index=True)
