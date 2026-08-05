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
    # Private server-side path; never included in API serialization.
    pdf_file_path = db.Column(db.String(500), nullable=False)
    file_sha256 = db.Column(db.String(64), nullable=True)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parsing_template_id = db.Column(
        db.Integer,
        db.ForeignKey('parsing_templates.id'),
        nullable=True,
        index=True
    )
    status = db.Column(db.String(20), default='uploaded', nullable=False, index=True)
    # Status values: uploading, uploaded, parsing, review, approving, approved,
    # failed, and deleting. Transitional states make write operations
    # retry-safe.
    error_message = db.Column(db.Text, nullable=True)
    parsing_started_at = db.Column(db.DateTime, nullable=True)
    parsed_data = db.Column(db.JSON, nullable=True)  # Temporary storage for review workflow
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bank_account = db.relationship('BankAccount', back_populates='statements')
    transactions = db.relationship('Transaction', back_populates='statement',
                                   cascade='all, delete-orphan')
    parsing_template = db.relationship(
        'ParsingTemplate',
        foreign_keys=[parsing_template_id],
        back_populates='statements'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'bank_account_id',
            'file_sha256',
            name='uq_bank_statements_account_file_sha256',
        ),
    )

    # Indexes created in migration:
    # idx_statements_bank_account (bank_account_id)
    # idx_statements_status (status)

    def __repr__(self):
        return (f'<BankStatement {self.statement_period_start} to {self.statement_period_end} '
                f'status={self.status}>')

    def to_dict(self, *, include_parsed_data=True):
        """Return the public statement representation.

        The server-side PDF path is deliberately never serialized. It reveals
        storage layout and is only needed by the parsing service.
        """
        data = {
            'id': self.id,
            'bank_account_id': self.bank_account_id,
            'statement_period_start': (self.statement_period_start.isoformat()
                                      if self.statement_period_start else None),
            'statement_period_end': (self.statement_period_end.isoformat()
                                    if self.statement_period_end else None),
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'parsing_template_id': self.parsing_template_id,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_parsed_data:
            data['parsed_data'] = self.parsed_data
        return data

    def to_dict_with_transactions(self):
        """Convert statement to dictionary including transactions list"""
        data = self.to_dict()
        data['transactions'] = [t.to_dict() for t in self.transactions]
        return data
