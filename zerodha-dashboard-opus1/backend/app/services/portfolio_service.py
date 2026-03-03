"""
Portfolio service for calculations and aggregations.
"""
from typing import List, Dict, Optional
from datetime import datetime
from app.database import db
from app.models import Account, Holding, Snapshot, PortfolioTimeseries, SectorAllocation
import logging

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for portfolio calculations and multi-account aggregation"""

    @staticmethod
    def calculate_portfolio_summary(holdings: List[Holding]) -> Dict:
        """
        Calculate portfolio summary from holdings list.

        Args:
            holdings: List of Holding objects

        Returns:
            Dictionary with summary metrics
        """
        if not holdings:
            return {
                'total_holdings': 0,
                'total_investment': 0,
                'current_value': 0,
                'total_pnl': 0,
                'total_pnl_percentage': 0,
                'day_change': 0
            }

        total_investment = sum(
            float(h.quantity * h.average_price) for h in holdings
        )
        current_value = sum(
            float(h.current_value or 0) for h in holdings
        )
        total_pnl = current_value - total_investment
        total_pnl_percentage = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        day_change = sum(float(h.day_change or 0) for h in holdings)

        return {
            'total_holdings': len(holdings),
            'total_investment': round(total_investment, 2),
            'current_value': round(current_value, 2),
            'total_pnl': round(total_pnl, 2),
            'total_pnl_percentage': round(total_pnl_percentage, 2),
            'day_change': round(day_change, 2)
        }

    @staticmethod
    def aggregate_accounts(account_ids: List[int] = None) -> Dict:
        """
        Aggregate portfolio data across multiple accounts.

        Args:
            account_ids: List of account IDs to aggregate. If None, aggregates all active accounts.

        Returns:
            Aggregated portfolio dictionary
        """
        query = db.session.query(Holding).join(Account)

        if account_ids:
            query = query.filter(Holding.account_id.in_(account_ids))
        else:
            query = query.filter(Account.is_active == True)

        # Get latest holdings (from most recent snapshot)
        latest_snapshot = db.session.query(Snapshot).order_by(Snapshot.snapshot_date.desc()).first()
        if latest_snapshot:
            query = query.filter(Holding.snapshot_id == latest_snapshot.id)

        holdings = query.all()

        summary = PortfolioService.calculate_portfolio_summary(holdings)
        summary['holdings'] = [h.to_dict() for h in holdings]

        return summary

    @staticmethod
    def calculate_sector_breakdown(holdings: List[Holding]) -> List[Dict]:
        """
        Calculate sector-wise allocation and performance.

        Args:
            holdings: List of Holding objects

        Returns:
            List of sector allocation dictionaries
        """
        if not holdings:
            return []

        # Group by sector
        sector_data = {}
        total_value = sum(float(h.current_value or 0) for h in holdings)

        for holding in holdings:
            sector = holding.sector or 'Other'

            if sector not in sector_data:
                sector_data[sector] = {
                    'sector': sector,
                    'total_value': 0,
                    'pnl': 0,
                    'holdings_count': 0
                }

            sector_data[sector]['total_value'] += float(holding.current_value or 0)
            sector_data[sector]['pnl'] += float(holding.pnl or 0)
            sector_data[sector]['holdings_count'] += 1

        # Calculate allocation percentages
        sectors = []
        for sector, data in sector_data.items():
            data['allocation_percentage'] = (data['total_value'] / total_value * 100) if total_value > 0 else 0
            data['allocation_percentage'] = round(data['allocation_percentage'], 2)
            data['total_value'] = round(data['total_value'], 2)
            data['pnl'] = round(data['pnl'], 2)
            sectors.append(data)

        # Sort by allocation percentage
        sectors.sort(key=lambda x: x['allocation_percentage'], reverse=True)

        return sectors

    @staticmethod
    def create_snapshot(snapshot_date: datetime = None) -> Snapshot:
        """
        Create a portfolio snapshot.

        Args:
            snapshot_date: Snapshot timestamp (defaults to now)

        Returns:
            Created Snapshot object
        """
        if snapshot_date is None:
            snapshot_date = datetime.utcnow()

        # Get all active accounts
        accounts = Account.query.filter_by(is_active=True).all()

        # Calculate total portfolio metrics across all accounts
        all_holdings = []
        for account in accounts:
            # Holdings would be fetched and stored before calling this
            pass

        # For now, create empty snapshot
        snapshot = Snapshot(
            snapshot_date=snapshot_date,
            total_holdings=0,
            total_investment=0,
            current_value=0,
            total_pnl=0,
            total_pnl_percentage=0
        )

        db.session.add(snapshot)
        db.session.commit()

        logger.info(f"Created snapshot #{snapshot.id} at {snapshot_date}")
        return snapshot

    @staticmethod
    def get_top_performers(holdings: List[Holding], limit: int = 5) -> List[Dict]:
        """
        Get top performing holdings by P&L percentage.

        Args:
            holdings: List of Holding objects
            limit: Number of top performers to return

        Returns:
            List of top performer dictionaries
        """
        sorted_holdings = sorted(
            holdings,
            key=lambda h: float(h.pnl_percentage or 0),
            reverse=True
        )

        return [h.to_dict() for h in sorted_holdings[:limit]]

    @staticmethod
    def get_worst_performers(holdings: List[Holding], limit: int = 5) -> List[Dict]:
        """
        Get worst performing holdings by P&L percentage.

        Args:
            holdings: List of Holding objects
            limit: Number of worst performers to return

        Returns:
            List of worst performer dictionaries
        """
        sorted_holdings = sorted(
            holdings,
            key=lambda h: float(h.pnl_percentage or 0)
        )

        return [h.to_dict() for h in sorted_holdings[:limit]]

    @staticmethod
    def get_portfolio_allocation(holdings: List[Holding]) -> List[Dict]:
        """
        Get portfolio allocation by stock.

        Args:
            holdings: List of Holding objects

        Returns:
            List of allocation dictionaries
        """
        total_value = sum(float(h.current_value or 0) for h in holdings)

        allocation = []
        for holding in holdings:
            value = float(holding.current_value or 0)
            percentage = (value / total_value * 100) if total_value > 0 else 0

            allocation.append({
                'tradingsymbol': holding.tradingsymbol,
                'value': round(value, 2),
                'percentage': round(percentage, 2)
            })

        # Sort by percentage
        allocation.sort(key=lambda x: x['percentage'], reverse=True)

        return allocation
