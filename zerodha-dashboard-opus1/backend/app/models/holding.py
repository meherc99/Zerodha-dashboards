"""
Holding model for storing stock and mutual fund holdings.
"""
from datetime import datetime
from app.database import db


class Holding(db.Model):
    """Model for storing individual stock/MF holdings"""

    __tablename__ = 'holdings'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    snapshot_id = db.Column(db.Integer, db.ForeignKey('snapshots.id', ondelete='SET NULL'))

    # Instrument details
    tradingsymbol = db.Column(db.String(50), nullable=False)
    instrument_type = db.Column(db.String(10), nullable=False)  # 'equity' or 'mf'
    exchange = db.Column(db.String(10))
    isin = db.Column(db.String(20))

    # Quantity and pricing
    quantity = db.Column(db.Integer, nullable=False)
    average_price = db.Column(db.Numeric(15, 2), nullable=False)
    last_price = db.Column(db.Numeric(15, 2), nullable=False)

    # P&L calculations
    pnl = db.Column(db.Numeric(15, 2))
    pnl_percentage = db.Column(db.Numeric(8, 2))
    day_change = db.Column(db.Numeric(15, 2))
    day_change_percentage = db.Column(db.Numeric(8, 2))
    current_value = db.Column(db.Numeric(15, 2))

    # Additional metadata
    purchase_date = db.Column(db.Date)
    sector = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    account = db.relationship('Account', back_populates='holdings')
    snapshot = db.relationship('Snapshot', back_populates='holdings')

    # Unique constraint: one holding per symbol per snapshot per account
    __table_args__ = (
        db.UniqueConstraint('snapshot_id', 'account_id', 'tradingsymbol', name='_snapshot_account_symbol_uc'),
        db.Index('idx_holdings_account', 'account_id'),
        db.Index('idx_holdings_snapshot', 'snapshot_id'),
        db.Index('idx_holdings_symbol', 'tradingsymbol'),
        db.Index('idx_holdings_type', 'instrument_type'),
    )

    def __repr__(self):
        return f'<Holding {self.tradingsymbol} ({self.instrument_type})>'

    def to_dict(self):
        """Convert holding to dictionary"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'tradingsymbol': self.tradingsymbol,
            'exchange': self.exchange,
            'instrument_type': self.instrument_type,
            'isin': self.isin,
            'quantity': self.quantity,
            'average_price': float(self.average_price) if self.average_price else 0,
            'last_price': float(self.last_price) if self.last_price else 0,
            'current_value': float(self.current_value) if self.current_value else 0,
            'pnl': float(self.pnl) if self.pnl else 0,
            'pnl_percentage': float(self.pnl_percentage) if self.pnl_percentage else 0,
            'day_change': float(self.day_change) if self.day_change else 0,
            'day_change_percentage': float(self.day_change_percentage) if self.day_change_percentage else 0,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'sector': self.sector
        }
