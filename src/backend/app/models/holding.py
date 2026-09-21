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
    holding_key = db.Column(db.String(255), nullable=False)
    tradingsymbol = db.Column(db.String(100), nullable=False)
    instrument_type = db.Column(db.String(20), nullable=False)  # 'equity', 'mf', or 'us_equity'
    market = db.Column(db.String(10), default='IN')  # 'IN' or 'US'
    exchange = db.Column(db.String(10))
    isin = db.Column(db.String(20))
    folio = db.Column(db.String(100))
    currency = db.Column(db.String(3), nullable=False, default='INR')

    # Quantity and pricing
    quantity = db.Column(db.Numeric(20, 6), nullable=False)
    average_price = db.Column(db.Numeric(20, 6), nullable=False)
    last_price = db.Column(db.Numeric(20, 6), nullable=False)
    last_price_date = db.Column(db.Date)

    # P&L calculations
    pnl = db.Column(db.Numeric(15, 2))
    pnl_percentage = db.Column(db.Numeric(8, 2))
    day_change = db.Column(db.Numeric(15, 2))
    day_change_percentage = db.Column(db.Numeric(8, 2))
    current_value = db.Column(db.Numeric(15, 2))

    # Additional metadata
    purchase_date = db.Column(db.Date)
    maturity_date = db.Column(db.Date)
    interest_rate = db.Column(db.Numeric(7, 4))
    sector = db.Column(db.String(50))
    source = db.Column(db.String(30))
    valued_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    account = db.relationship('Account', back_populates='holdings')
    snapshot = db.relationship('Snapshot', back_populates='holdings')

    # A source-aware key allows separate MF folios and same-name deposits.
    __table_args__ = (
        db.UniqueConstraint(
            'snapshot_id',
            'account_id',
            'holding_key',
            name='uq_holding_snapshot_account_key',
        ),
        db.Index('idx_holdings_account', 'account_id'),
        db.Index('idx_holdings_snapshot', 'snapshot_id'),
        db.Index('idx_holdings_symbol', 'tradingsymbol'),
        db.Index('idx_holdings_type', 'instrument_type'),
    )

    def __repr__(self):
        return f'<Holding {self.tradingsymbol} ({self.instrument_type})>'

    def to_dict(self):
        """Convert holding to dictionary"""
        quantity = float(self.quantity) if self.quantity is not None else 0
        average_price = float(self.average_price) if self.average_price else 0
        last_price = float(self.last_price) if self.last_price else 0
        current_value = float(self.current_value) if self.current_value else 0

        stored_pnl = float(self.pnl) if self.pnl else 0
        stored_pnl_pct = float(self.pnl_percentage) if self.pnl_percentage else 0

        # Recompute pnl from prices when the stored value is zero but prices differ.
        # This corrects records that were synced before the kite_service fallback was
        # applied (the Kite MF API returns pnl=0 rather than null).
        investment = quantity * average_price
        if stored_pnl == 0 and investment and current_value:
            computed_pnl = current_value - investment
            pnl = computed_pnl
            pnl_pct = (computed_pnl / investment * 100) if investment else 0
        else:
            pnl = stored_pnl
            pnl_pct = stored_pnl_pct if stored_pnl_pct else (
                (stored_pnl / investment * 100) if investment else 0
            )

        return {
            'id': self.id,
            'account_id': self.account_id,
            'account_name': self.account.account_name if self.account else None,
            'snapshot_id': self.snapshot_id,
            'holding_key': self.holding_key,
            'tradingsymbol': self.tradingsymbol,
            'exchange': self.exchange,
            'instrument_type': self.instrument_type,
            'market': self.market,
            'isin': self.isin,
            'folio': self.folio,
            'currency': self.currency,
            'quantity': quantity,
            'average_price': average_price,
            'last_price': last_price,
            'last_price_date': self.last_price_date.isoformat() if self.last_price_date else None,
            'current_value': current_value,
            'pnl': round(pnl, 2),
            'pnl_percentage': round(pnl_pct, 2),
            'day_change': float(self.day_change) if self.day_change else 0,
            'day_change_percentage': float(self.day_change_percentage) if self.day_change_percentage else 0,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'maturity_date': self.maturity_date.isoformat() if self.maturity_date else None,
            'interest_rate': float(self.interest_rate) if self.interest_rate is not None else None,
            'sector': self.sector,
            'source': self.source,
            'valued_at': self.valued_at.isoformat() if self.valued_at else None,
        }
