"""Server-side revocation records for logged-out JWT access tokens."""
from datetime import datetime

from app.database import db


class RevokedToken(db.Model):
    """A JWT identifier that must no longer authorize API requests."""

    __tablename__ = 'revoked_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
