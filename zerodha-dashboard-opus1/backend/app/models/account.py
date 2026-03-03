"""
Account model for storing Zerodha account credentials.
"""
from datetime import datetime
from app.database import db


class Account(db.Model):
    """Model for storing multiple family member Zerodha accounts"""

    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False, unique=True)

    # Encrypted credentials
    api_key_encrypted = db.Column(db.Text, nullable=False)
    api_secret_encrypted = db.Column(db.Text, nullable=False)
    access_token_encrypted = db.Column(db.Text)
    request_token_encrypted = db.Column(db.Text)

    # Status and metadata
    is_active = db.Column(db.Boolean, default=True)
    last_synced_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    holdings = db.relationship('Holding', back_populates='account', cascade='all, delete-orphan')
    timeseries = db.relationship('PortfolioTimeseries', back_populates='account', cascade='all, delete-orphan')
    sector_allocations = db.relationship('SectorAllocation', back_populates='account', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Account {self.account_name}>'

    def to_dict(self):
        """Convert account to dictionary (excluding sensitive data)"""
        return {
            'id': self.id,
            'account_name': self.account_name,
            'is_active': self.is_active,
            'last_synced_at': self.last_synced_at.isoformat() if self.last_synced_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
