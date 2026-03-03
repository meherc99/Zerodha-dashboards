"""
Analytics service for advanced calculations and metrics.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.database import db
from app.models import PortfolioTimeseries, Holding, HistoricalPrice
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for advanced portfolio analytics"""

    @staticmethod
    def get_portfolio_history(
        account_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = 'daily'
    ) -> List[Dict]:
        """
        Get historical portfolio value data.

        Args:
            account_id: Specific account ID or None for all accounts
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            granularity: 'daily', 'weekly', 'monthly'

        Returns:
            List of timeseries data points
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        query = db.session.query(PortfolioTimeseries).filter(
            PortfolioTimeseries.date >= start_date,
            PortfolioTimeseries.date <= end_date
        )

        if account_id:
            query = query.filter(PortfolioTimeseries.account_id == account_id)

        query = query.order_by(PortfolioTimeseries.date.asc())
        timeseries = query.all()

        # Group by account if needed
        if not account_id:
            # Aggregate across accounts for each date
            df = pd.DataFrame([t.to_dict() for t in timeseries])
            if not df.empty:
                grouped = df.groupby('date').agg({
                    'total_value': 'sum',
                    'invested_value': 'sum',
                    'pnl': 'sum',
                    'day_change': 'sum',
                    'holdings_count': 'sum'
                }).reset_index()

                # Recalculate pnl_percentage
                grouped['pnl_percentage'] = (
                    grouped['pnl'] / grouped['invested_value'] * 100
                ).fillna(0)

                return grouped.to_dict('records')

        return [t.to_dict() for t in timeseries]

    @staticmethod
    def calculate_returns(timeseries_data: List[Dict]) -> Dict:
        """
        Calculate various return metrics.

        Args:
            timeseries_data: List of timeseries data points

        Returns:
            Dictionary with return metrics
        """
        if not timeseries_data or len(timeseries_data) < 2:
            return {
                'total_return': 0,
                'annualized_return': 0,
                'day_return': 0
            }

        df = pd.DataFrame(timeseries_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Total return
        initial_value = df.iloc[0]['total_value']
        final_value = df.iloc[-1]['total_value']
        total_return = ((final_value - initial_value) / initial_value * 100) if initial_value > 0 else 0

        # Annualized return
        days = (df.iloc[-1]['date'] - df.iloc[0]['date']).days
        if days > 0:
            annualized_return = ((final_value / initial_value) ** (365 / days) - 1) * 100 if initial_value > 0 else 0
        else:
            annualized_return = 0

        # Day return (latest day change)
        day_return = df.iloc[-1].get('day_change', 0)

        return {
            'total_return': round(total_return, 2),
            'annualized_return': round(annualized_return, 2),
            'day_return': round(day_return, 2)
        }

    @staticmethod
    def calculate_risk_metrics(timeseries_data: List[Dict]) -> Dict:
        """
        Calculate risk metrics (volatility, Sharpe ratio, max drawdown).

        Args:
            timeseries_data: List of timeseries data points

        Returns:
            Dictionary with risk metrics
        """
        if not timeseries_data or len(timeseries_data) < 2:
            return {
                'volatility': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }

        df = pd.DataFrame(timeseries_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Calculate daily returns
        df['returns'] = df['total_value'].pct_change()

        # Volatility (annualized standard deviation of returns)
        volatility = df['returns'].std() * np.sqrt(252) * 100  # Annualized

        # Sharpe Ratio (assuming risk-free rate of 0 for simplicity)
        mean_return = df['returns'].mean() * 252  # Annualized
        sharpe_ratio = mean_return / (volatility / 100) if volatility > 0 else 0

        # Max Drawdown
        df['cumulative'] = (1 + df['returns']).cumprod()
        df['running_max'] = df['cumulative'].cummax()
        df['drawdown'] = (df['cumulative'] - df['running_max']) / df['running_max'] * 100
        max_drawdown = df['drawdown'].min()

        return {
            'volatility': round(volatility, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2)
        }

    @staticmethod
    def calculate_correlation_matrix(
        symbols: List[str],
        period_days: int = 90
    ) -> Dict:
        """
        Calculate correlation matrix for given symbols.

        Args:
            symbols: List of trading symbols
            period_days: Number of days to look back

        Returns:
            Dictionary with correlation matrix and symbols
        """
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=period_days)

        # Fetch historical data for all symbols
        price_data = {}
        for symbol in symbols:
            prices = db.session.query(HistoricalPrice).filter(
                HistoricalPrice.tradingsymbol == symbol,
                HistoricalPrice.date >= start_date,
                HistoricalPrice.date <= end_date
            ).order_by(HistoricalPrice.date.asc()).all()

            if prices:
                price_data[symbol] = pd.DataFrame([
                    {'date': p.date, 'close': float(p.close)}
                    for p in prices
                ])

        if not price_data or len(price_data) < 2:
            return {
                'symbols': symbols,
                'matrix': [],
                'period_days': period_days
            }

        # Create combined DataFrame
        df_dict = {}
        for symbol, df in price_data.items():
            df = df.set_index('date')
            df_dict[symbol] = df['close']

        combined_df = pd.DataFrame(df_dict)

        # Calculate correlation matrix
        corr_matrix = combined_df.corr()

        return {
            'symbols': list(corr_matrix.columns),
            'matrix': corr_matrix.values.tolist(),
            'period_days': period_days
        }

    @staticmethod
    def generate_heatmap_data(
        holdings: List[Holding],
        metric: str = 'pnl_percentage',
        period: str = 'week'
    ) -> List[Dict]:
        """
        Generate performance heatmap data.

        Args:
            holdings: List of holdings
            metric: Metric to display ('pnl_percentage', 'day_change', etc.)
            period: Time period ('week', 'month', 'quarter', 'year')

        Returns:
            List of heatmap data points
        """
        # This would typically fetch historical snapshots and calculate changes
        # For now, return current data
        heatmap_data = []

        for holding in holdings:
            value = getattr(holding, metric, 0)
            heatmap_data.append({
                'symbol': holding.tradingsymbol,
                'value': float(value or 0),
                'sector': holding.sector
            })

        return heatmap_data

    @staticmethod
    def get_performance_metrics(
        account_id: Optional[int] = None,
        period_days: int = 30
    ) -> Dict:
        """
        Get comprehensive performance metrics.

        Args:
            account_id: Optional account ID
            period_days: Period for calculations

        Returns:
            Dictionary with all performance metrics
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)

        # Get timeseries data
        timeseries = AnalyticsService.get_portfolio_history(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date
        )

        # Calculate metrics
        returns = AnalyticsService.calculate_returns(timeseries)
        risk_metrics = AnalyticsService.calculate_risk_metrics(timeseries)

        return {
            'returns': returns,
            'risk_metrics': risk_metrics,
            'period_days': period_days
        }
