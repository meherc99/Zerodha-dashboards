"""
BankAccount model for managing user bank accounts.
"""
from datetime import datetime
from app.database import db
from app.utils.encryption import get_encryptor


class BankAccount(db.Model):
    """Model for user bank accounts"""

    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number_encrypted = db.Column(db.Text, nullable=False)
    account_number_last4 = db.Column(db.String(4), nullable=False)
    account_type = db.Column(db.String(20), default='savings')
    opening_balance = db.Column(
        db.Numeric(15, 2),
        default=0,
        nullable=False,
    )
    current_balance = db.Column(db.Numeric(15, 2), default=0)
    currency = db.Column(db.String(3), default='INR')
    last_statement_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='bank_accounts')
    transactions = db.relationship('Transaction', back_populates='bank_account',
                                   cascade='all, delete-orphan')
    statements = db.relationship('BankStatement', back_populates='bank_account',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return (
            f'<BankAccount {self.bank_name} - '
            f'{self.masked_account_number}>'
        )

    @property
    def account_number(self):
        """Decrypt the account number only for explicit server-side use."""
        return get_encryptor().decrypt(self.account_number_encrypted)

    @account_number.setter
    def account_number(self, value):
        normalized = str(value or '').strip()
        if len(normalized) < 4:
            raise ValueError('Account number must contain at least 4 characters')
        self.account_number_encrypted = get_encryptor().encrypt(normalized)
        self.account_number_last4 = normalized[-4:]

    @property
    def masked_account_number(self):
        """Return only enough account-number data for user identification."""
        return (
            f'****{self.account_number_last4}'
            if self.account_number_last4
            else ''
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'account_number': self.masked_account_number,
            'account_type': self.account_type,
            'opening_balance': str(self.opening_balance),
            'current_balance': str(self.current_balance),
            'currency': self.currency,
            'last_statement_date': self.last_statement_date.isoformat() if self.last_statement_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
