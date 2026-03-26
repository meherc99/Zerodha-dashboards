"""
Transaction model for storing parsed bank transactions.
"""
from datetime import datetime
from app.database import db


class Transaction(db.Model):
    """Model for bank transactions with categorization and search capabilities"""

    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    statement_id = db.Column(db.Integer, nullable=True, index=True)  # Forward reference - will add FK later
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id', ondelete='CASCADE'),
                                nullable=False, index=True)
    transaction_date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    merchant_name = db.Column(db.String(200))
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # 'credit' or 'debit'
    running_balance = db.Column(db.Numeric(15, 2))
    category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'),
                           nullable=True, index=True)
    category_confidence = db.Column(db.Float)  # 0-1 score from AI categorization
    verified = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank_account = db.relationship('BankAccount', back_populates='transactions')
    category = db.relationship('TransactionCategory', back_populates='transactions')
    # Forward reference for statement relationship (will be added when BankStatement model is created)
    # statement = db.relationship('BankStatement', back_populates='transactions')

    # Indexes will be created in migration:
    # idx_transactions_bank_account_date (bank_account_id, transaction_date DESC)
    # idx_transactions_category (category_id)
    # idx_transactions_filters (bank_account_id, transaction_date, transaction_type, category_id)

    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.amount} on {self.transaction_date}>'

    def to_dict(self):
        """Convert transaction to dictionary"""
        return {
            'id': self.id,
            'statement_id': self.statement_id,
            'bank_account_id': self.bank_account_id,
            'transaction_date': self.transaction_date.isoformat() if self.transaction_date else None,
            'description': self.description,
            'merchant_name': self.merchant_name,
            'amount': str(self.amount) if self.amount is not None else None,
            'transaction_type': self.transaction_type,
            'running_balance': str(self.running_balance) if self.running_balance is not None else None,
            'category_id': self.category_id,
            'category_confidence': self.category_confidence,
            'verified': self.verified,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
