"""
ParsingTemplate model for storing successful PDF extraction patterns.

This enables the incremental intelligence feature - first upload uses AI/table detection,
subsequent uploads use saved templates for instant processing.
"""
from datetime import datetime
from app.database import db


class ParsingTemplate(db.Model):
    """Model for saving PDF parsing templates to speed up future extractions"""

    __tablename__ = 'parsing_templates'

    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False, index=True)
    template_version = db.Column(db.Integer, default=1, nullable=False)
    extraction_config = db.Column(db.JSON, nullable=False)
    # extraction_config format:
    # {
    #   "table_area": [x1, y1, x2, y2],  # PDF coordinates (optional)
    #   "columns": {
    #     "date": 0,
    #     "description": 1,
    #     "withdrawal": 2,
    #     "deposit": 3,
    #     "balance": 4
    #   },
    #   "date_format": "%d/%m/%Y",
    #   "header_rows": 2,
    #   "footer_keywords": ["*** End of Statement ***"],
    #   "currency_symbol": "₹",
    #   "parsing_method": "pdfplumber" or "ai"
    # }
    success_count = db.Column(db.Integer, default=0, nullable=False)
    failure_count = db.Column(db.Integer, default=0, nullable=False)
    last_used_at = db.Column(db.DateTime)
    created_from_statement_id = db.Column(
        db.Integer,
        db.ForeignKey('bank_statements.id'),
        nullable=True
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    statements = db.relationship(
        'BankStatement',
        foreign_keys='BankStatement.parsing_template_id',
        back_populates='parsing_template'
    )
    created_from_statement = db.relationship(
        'BankStatement',
        foreign_keys=[created_from_statement_id],
        backref='spawned_templates'
    )

    # Composite index for efficient template lookup
    __table_args__ = (
        db.Index('idx_parsing_templates_bank_active', 'bank_name', 'is_active'),
    )

    def __repr__(self):
        return f'<ParsingTemplate {self.bank_name} v{self.template_version} (success: {self.success_count})>'

    def to_dict(self):
        """Convert template to dictionary"""
        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'template_version': self.template_version,
            'extraction_config': self.extraction_config,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'created_from_statement_id': self.created_from_statement_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def mark_success(self):
        """Increment success count and update last_used_at"""
        self.success_count += 1
        self.last_used_at = datetime.utcnow()

    def mark_failure(self):
        """Increment failure count and potentially deactivate if too many failures"""
        self.failure_count += 1
        # Deactivate template if failure rate is too high (>30% and at least 5 failures)
        if self.failure_count >= 5:
            failure_rate = self.failure_count / (self.success_count + self.failure_count)
            if failure_rate > 0.3:
                self.is_active = False
