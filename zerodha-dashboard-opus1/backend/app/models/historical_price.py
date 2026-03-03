"""
Historical price model for correlation analysis.
"""
from datetime import datetime
from app.database import db


class HistoricalPrice(db.Model):
    """Model for storing historical price data for correlation analysis"""

    __tablename__ = 'historical_prices'

    id = db.Column(db.Integer, primary_key=True)
    tradingsymbol = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)

    # OHLC data
    open = db.Column(db.Numeric(15, 2))
    high = db.Column(db.Numeric(15, 2))
    low = db.Column(db.Numeric(15, 2))
    close = db.Column(db.Numeric(15, 2), nullable=False)
    volume = db.Column(db.BigInteger)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('tradingsymbol', 'date', name='_symbol_date_uc'),
        db.Index('idx_historical_prices_symbol_date', 'tradingsymbol', 'date', postgresql_ops={'date': 'DESC'}),
    )

    def __repr__(self):
        return f'<HistoricalPrice {self.tradingsymbol} {self.date}>'

    def to_dict(self):
        """Convert historical price to dictionary"""
        return {
            'tradingsymbol': self.tradingsymbol,
            'date': self.date.isoformat() if self.date else None,
            'open': float(self.open) if self.open else 0,
            'high': float(self.high) if self.high else 0,
            'low': float(self.low) if self.low else 0,
            'close': float(self.close) if self.close else 0,
            'volume': self.volume
        }
