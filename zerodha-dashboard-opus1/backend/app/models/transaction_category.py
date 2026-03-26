"""
TransactionCategory model for organizing bank transactions.
"""
from datetime import datetime
from app.database import db


class TransactionCategory(db.Model):
    """Model for transaction categories with hierarchical support"""

    __tablename__ = 'transaction_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    icon = db.Column(db.String(10))  # emoji or icon class
    color = db.Column(db.String(7))  # hex color code
    parent_category_id = db.Column(db.Integer, db.ForeignKey('transaction_categories.id'))
    keywords = db.Column(db.JSON, default=list)  # list of keywords for auto-categorization
    is_system = db.Column(db.Boolean, default=True)  # system vs user-created
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Self-referential relationship for hierarchical categories
    children = db.relationship(
        'TransactionCategory',
        backref=db.backref('parent', remote_side=[id]),
        cascade='all, delete-orphan'
    )

    # Forward reference to Transaction model (will be created later)
    # transactions = db.relationship('Transaction', back_populates='category')

    def __repr__(self):
        return f'<TransactionCategory {self.name}>'

    def to_dict(self):
        """Convert category to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'color': self.color,
            'parent_category_id': self.parent_category_id,
            'keywords': self.keywords if self.keywords else [],
            'is_system': self.is_system,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
