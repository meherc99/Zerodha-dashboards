"""
BankStatement model for tracking uploaded PDF bank statements and their parsing status.
"""
from datetime import datetime
from app.database import db


class BankStatement(db.Model):
    """Model for bank statements with PDF parsing workflow"""

    __tablename__ = 'bank_statements'

    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id', ondelete='CASCADE'),
                               nullable=False, index=True)
    statement_period_start = db.Column(db.Date, nullable=False)
    statement_period_end = db.Column(db.Date, nullable=False)
    pdf_file_path = db.Column(db.String(500), nullable=False)  # Encrypted path to uploaded PDF
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parsing_template_id = db.Column(db.Integer, nullable=True)  # Forward reference - will add FK later
    status = db.Column(db.String(20), default='uploaded', nullable=False, index=True)
    # Status values: 'uploaded', 'parsing', 'review', 'approved', 'failed'
    error_message = db.Column(db.Text, nullable=True)
    parsed_data = db.Column(db.JSON, nullable=True)  # Temporary storage for review workflow
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bank_account = db.relationship('BankAccount', back_populates='statements')
    transactions = db.relationship('Transaction', back_populates='statement',
                                   cascade='all, delete-orphan')
    # parsing_template relationship will be added when ParsingTemplate model is created

    # Indexes created in migration:
    # idx_statements_bank_account (bank_account_id)
    # idx_statements_status (status)

    def __repr__(self):
        return (f'<BankStatement {self.statement_period_start} to {self.statement_period_end} '
                f'status={self.status}>')

    def to_dict(self):
        """Convert statement to dictionary"""
        return {
            'id': self.id,
            'bank_account_id': self.bank_account_id,
            'statement_period_start': (self.statement_period_start.isoformat()
                                      if self.statement_period_start else None),
            'statement_period_end': (self.statement_period_end.isoformat()
                                    if self.statement_period_end else None),
            'pdf_file_path': self.pdf_file_path,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'parsing_template_id': self.parsing_template_id,
            'status': self.status,
            'error_message': self.error_message,
            'parsed_data': self.parsed_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def to_dict_with_transactions(self):
        """Convert statement to dictionary including transactions list"""
        data = self.to_dict()
        data['transactions'] = [t.to_dict() for t in self.transactions]
        return data
