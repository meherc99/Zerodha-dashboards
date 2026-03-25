"""
BankAccount model for managing user bank accounts.
"""
from datetime import datetime
from app.database import db


class BankAccount(db.Model):
    """Model for user bank accounts"""

    __tablename__ = 'bank_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'),
                       nullable=False, index=True)
    bank_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    account_type = db.Column(db.String(20), default='savings')
    current_balance = db.Column(db.Numeric(15, 2), default=0)
    currency = db.Column(db.String(3), default='INR')
    last_statement_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', back_populates='bank_accounts')
    # Forward references for future relationships
    # statements = db.relationship('BankStatement', back_populates='account',
    #                             cascade='all, delete-orphan')
    # transactions = db.relationship('Transaction', back_populates='account',
    #                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<BankAccount {self.bank_name} - {self.account_number}>'

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_type': self.account_type,
            'current_balance': str(self.current_balance),
            'currency': self.currency,
            'last_statement_date': self.last_statement_date.isoformat() if self.last_statement_date else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
