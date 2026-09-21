"""
Snapshot models for storing portfolio state at specific points in time.
"""
from datetime import datetime
import uuid

from app.database import db


class Snapshot(db.Model):
    """Model for portfolio snapshots taken at specific times"""

    __tablename__ = 'snapshots'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey('accounts.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    batch_id = db.Column(
        db.String(36),
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    snapshot_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='completed')
    trigger = db.Column(db.String(20), nullable=False, default='manual')
    error_message = db.Column(db.String(255))

    # Portfolio summary
    total_holdings = db.Column(db.Integer, default=0)
    total_investment = db.Column(db.Numeric(15, 2))
    current_value = db.Column(db.Numeric(15, 2))
    total_pnl = db.Column(db.Numeric(15, 2))
    total_pnl_percentage = db.Column(db.Numeric(8, 2))
    currency = db.Column(db.String(8))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    account = db.relationship('Account', back_populates='snapshots')
    holdings = db.relationship('Holding', back_populates='snapshot', cascade='all, delete-orphan')
    sector_allocations = db.relationship('SectorAllocation', back_populates='snapshot', cascade='all, delete-orphan')

    __table_args__ = (
        db.UniqueConstraint(
            'account_id',
            'snapshot_date',
            name='uq_snapshots_account_date',
        ),
        db.Index('idx_snapshots_account_status_date', 'account_id', 'status', 'snapshot_date'),
        db.Index('idx_snapshots_date', 'snapshot_date', postgresql_ops={'snapshot_date': 'DESC'}),
    )

    def __repr__(self):
        return f'<Snapshot {self.snapshot_date}>'

    def to_dict(self):
        """Convert snapshot to dictionary"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'batch_id': self.batch_id,
            'snapshot_date': self.snapshot_date.isoformat() if self.snapshot_date else None,
            'status': self.status,
            'trigger': self.trigger,
            'error_message': self.error_message,
            'total_holdings': self.total_holdings,
            'total_investment': (
                float(self.total_investment)
                if self.total_investment is not None
                else None
            ),
            'current_value': (
                float(self.current_value)
                if self.current_value is not None
                else None
            ),
            'total_pnl': (
                float(self.total_pnl)
                if self.total_pnl is not None
                else None
            ),
            'total_pnl_percentage': (
                float(self.total_pnl_percentage)
                if self.total_pnl_percentage is not None
                else None
            ),
            'currency': self.currency,
        }


class PortfolioTimeseries(db.Model):
    """Model for tracking portfolio value over time"""

    __tablename__ = 'portfolio_timeseries'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', ondelete='CASCADE'), nullable=False)
    snapshot_id = db.Column(db.Integer, db.ForeignKey('snapshots.id', ondelete='SET NULL'))
    date = db.Column(db.DateTime, nullable=False)

    # Portfolio values
    total_value = db.Column(db.Numeric(15, 2), nullable=False)
    invested_value = db.Column(db.Numeric(15, 2), nullable=False)
    pnl = db.Column(db.Numeric(15, 2))
    pnl_percentage = db.Column(db.Numeric(8, 2))
    day_change = db.Column(db.Numeric(15, 2))
    holdings_count = db.Column(db.Integer)
    currency = db.Column(db.String(3), nullable=False, default='INR')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    account = db.relationship('Account', back_populates='timeseries')

    __table_args__ = (
        db.UniqueConstraint('account_id', 'date', 'currency', name='uq_account_date_currency'),
        db.Index('idx_portfolio_ts_account_date', 'account_id', 'date', postgresql_ops={'date': 'DESC'}),
        db.Index('idx_portfolio_ts_date', 'date', postgresql_ops={'date': 'DESC'}),
    )

    def __repr__(self):
        return f'<PortfolioTimeseries Account:{self.account_id} Date:{self.date}>'

    def to_dict(self):
        """Convert timeseries entry to dictionary"""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'date': self.date.isoformat() if self.date else None,
            'total_value': float(self.total_value) if self.total_value else 0,
            'invested_value': float(self.invested_value) if self.invested_value else 0,
            'pnl': float(self.pnl) if self.pnl else 0,
            'pnl_percentage': float(self.pnl_percentage) if self.pnl_percentage else 0,
            'day_change': float(self.day_change) if self.day_change else 0,
            'holdings_count': self.holdings_count,
            'currency': self.currency,
        }


class SectorAllocation(db.Model):
    """Model for storing sector-wise allocation"""

    __tablename__ = 'sector_allocation'

    id = db.Column(db.Integer, primary_key=True)
    snapshot_id = db.Column(db.Integer, db.ForeignKey('snapshots.id', ondelete='CASCADE'))
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id', ondelete='CASCADE'))
    sector = db.Column(db.String(50), nullable=False)

    # Allocation metrics
    allocation_percentage = db.Column(db.Numeric(5, 2))
    total_value = db.Column(db.Numeric(15, 2))
    pnl = db.Column(db.Numeric(15, 2))
    currency = db.Column(db.String(3), nullable=False, default='INR')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    account = db.relationship('Account', back_populates='sector_allocations')
    snapshot = db.relationship('Snapshot', back_populates='sector_allocations')

    __table_args__ = (
        db.Index('idx_sector_allocation_snapshot', 'snapshot_id'),
    )

    def __repr__(self):
        return f'<SectorAllocation {self.sector}>'

    def to_dict(self):
        """Convert sector allocation to dictionary"""
        return {
            'id': self.id,
            'sector': self.sector,
            'allocation_percentage': float(self.allocation_percentage) if self.allocation_percentage else 0,
            'total_value': float(self.total_value) if self.total_value else 0,
            'pnl': float(self.pnl) if self.pnl else 0,
            'currency': self.currency
        }
