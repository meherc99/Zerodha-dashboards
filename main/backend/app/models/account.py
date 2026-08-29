"""
Account model for storing Zerodha account credentials.
"""
from datetime import datetime
from app.database import db


class Account(db.Model):
    """Model for storing multiple family member Zerodha accounts"""

    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)

    # Encrypted credentials (nullable when Kite Connect is not configured)
    api_key_encrypted = db.Column(db.Text, nullable=True)
    api_secret_encrypted = db.Column(db.Text, nullable=True)
    access_token_encrypted = db.Column(db.Text)
    request_token_encrypted = db.Column(db.Text)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    needs_reauth = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    portfolio_version = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        server_default='0',
    )
    last_synced_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='accounts')
    holdings = db.relationship('Holding', back_populates='account', cascade='all, delete-orphan')
    snapshots = db.relationship('Snapshot', back_populates='account', cascade='all, delete-orphan')
    timeseries = db.relationship('PortfolioTimeseries', back_populates='account', cascade='all, delete-orphan')
    sector_allocations = db.relationship('SectorAllocation', back_populates='account', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'account_name', name='uq_accounts_user_account_name'),
    )

    def __repr__(self):
        return f'<Account {self.account_name}>'

    def to_dict(self):
        """Convert account to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'account_name': self.account_name,
            'is_active': self.is_active,
            'needs_reauth': bool(self.needs_reauth),
            'has_kite_credentials': bool(self.api_key_encrypted and self.api_secret_encrypted),
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
