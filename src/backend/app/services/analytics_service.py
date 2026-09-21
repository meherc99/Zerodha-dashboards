"""
Analytics service for advanced calculations and metrics.
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import and_, func
from app.database import db
from app.models import Account, PortfolioTimeseries, Holding, HistoricalPrice
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for advanced portfolio analytics"""

    @staticmethod
    def get_portfolio_history(
        user_id: int,
        account_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = 'daily',
        currency: Optional[str] = None,
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

        scoped = (
            db.session.query(PortfolioTimeseries)
            .join(Account, Account.id == PortfolioTimeseries.account_id)
            .filter(
                Account.user_id == user_id,
                Account.is_active.is_(True),
            )
        )

        if account_id:
            scoped = scoped.filter(PortfolioTimeseries.account_id == account_id)
        if currency:
            scoped = scoped.filter(PortfolioTimeseries.currency == currency)

        baseline_dates = (
            db.session.query(
                PortfolioTimeseries.account_id.label('account_id'),
                PortfolioTimeseries.currency.label('currency'),
                func.max(PortfolioTimeseries.date).label('date'),
            )
            .join(Account, Account.id == PortfolioTimeseries.account_id)
            .filter(
                Account.user_id == user_id,
                Account.is_active.is_(True),
                PortfolioTimeseries.date < start_date,
            )
        )
        if account_id:
            baseline_dates = baseline_dates.filter(
                PortfolioTimeseries.account_id == account_id
            )
        if currency:
            baseline_dates = baseline_dates.filter(
                PortfolioTimeseries.currency == currency
            )
        baseline_dates = baseline_dates.group_by(
            PortfolioTimeseries.account_id,
            PortfolioTimeseries.currency,
        ).subquery()

        baseline = (
            db.session.query(PortfolioTimeseries)
            .join(
                baseline_dates,
                and_(
                    PortfolioTimeseries.account_id
                    == baseline_dates.c.account_id,
                    PortfolioTimeseries.currency
                    == baseline_dates.c.currency,
                    PortfolioTimeseries.date == baseline_dates.c.date,
                ),
            )
            .all()
        )
        events = (
            scoped.filter(
                PortfolioTimeseries.date >= start_date,
                PortfolioTimeseries.date <= end_date,
            )
            .order_by(PortfolioTimeseries.date.asc())
            .all()
        )

        state = {
            (entry.account_id, entry.currency): entry
            for entry in baseline
        }
        def period_for(value):
            if granularity == 'weekly':
                return (
                    value - timedelta(days=value.weekday())
                ).replace(hour=0, minute=0, second=0, microsecond=0)
            if granularity == 'monthly':
                return value.replace(
                    day=1,
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                )
            return value.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        period_events = {
            period_for(start_date): {},
            period_for(end_date): {},
        }
        for entry in events:
            period = period_for(entry.date)
            period_events.setdefault(period, {})[
                (entry.account_id, entry.currency)
            ] = entry

        records = []
        for period in sorted(period_events):
            updates = period_events[period]
            state.update(updates)
            currencies = sorted({key[1] for key in state})
            for code in currencies:
                entries = [
                    (key, entry)
                    for key, entry in state.items()
                    if key[1] == code
                ]
                invested = sum(float(entry.invested_value) for _, entry in entries)
                pnl = sum(float(entry.pnl or 0) for _, entry in entries)
                records.append(
                    {
                        'date': period.isoformat(),
                        'currency': code,
                        'total_value': round(
                            sum(float(entry.total_value) for _, entry in entries),
                            2,
                        ),
                        'invested_value': round(invested, 2),
                        'pnl': round(pnl, 2),
                        'pnl_percentage': round(
                            pnl / invested * 100 if invested else 0,
                            2,
                        ),
                        # A carried-forward account has no trustworthy current
                        # day movement for this event period.
                        'day_change': round(
                            sum(
                                float(entry.day_change or 0)
                                for key, entry in entries
                                if key in updates
                            ),
                            2,
                        ),
                        'holdings_count': sum(
                            int(entry.holdings_count or 0)
                            for _, entry in entries
                        ),
                        'accounts_count': len(entries),
                    }
                )
        return records

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
                'value_growth_percentage': 0,
                'annualized_value_growth_percentage': 0,
                'latest_day_change': 0,
                'cash_flow_adjusted': False,
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
            'value_growth_percentage': round(total_return, 2),
            'annualized_value_growth_percentage': round(
                annualized_return,
                2,
            ),
            'latest_day_change': round(day_return, 2),
            'cash_flow_adjusted': False,
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
                'value_change_volatility': 0,
                'value_change_sharpe_proxy': 0,
                'max_value_drawdown': 0,
                'cash_flow_adjusted': False,
            }

        df = pd.DataFrame(timeseries_data)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')

        # Calculate daily returns
        df['returns'] = df['total_value'].pct_change()

        # Volatility (annualized standard deviation of returns)
        volatility = df['returns'].std() * np.sqrt(252) * 100  # Annualized
        if pd.isna(volatility):
            volatility = 0

        # Sharpe Ratio (assuming risk-free rate of 0 for simplicity)
        mean_return = df['returns'].mean() * 252  # Annualized
        if pd.isna(mean_return):
            mean_return = 0
        sharpe_ratio = mean_return / (volatility / 100) if volatility > 0 else 0

        # Max Drawdown
        df['cumulative'] = (1 + df['returns']).cumprod()
        df['running_max'] = df['cumulative'].cummax()
        df['drawdown'] = (df['cumulative'] - df['running_max']) / df['running_max'] * 100
        max_drawdown = df['drawdown'].min()
        if pd.isna(max_drawdown):
            max_drawdown = 0

        return {
            'value_change_volatility': round(volatility, 2),
            'value_change_sharpe_proxy': round(sharpe_ratio, 2),
            'max_value_drawdown': round(max_drawdown, 2),
            'cash_flow_adjusted': False,
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
        user_id: int,
        account_id: Optional[int] = None,
        period_days: int = 30,
        currency: Optional[str] = None,
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
            user_id=user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            currency=currency,
        )

        by_currency = {}
        for code in sorted({point['currency'] for point in timeseries}):
            points = [point for point in timeseries if point['currency'] == code]
            by_currency[code] = {
                'value_growth': AnalyticsService.calculate_returns(points),
                'value_path_metrics': (
                    AnalyticsService.calculate_risk_metrics(points)
                ),
            }

        result = {
            'period_days': period_days,
            'currency': currency or (
                next(iter(by_currency)) if len(by_currency) == 1 else 'MIXED'
            ),
            'by_currency': by_currency,
        }
        if len(by_currency) == 1:
            result.update(next(iter(by_currency.values())))
        else:
            result.update({
                'value_growth': None,
                'value_path_metrics': None,
            })
        return result
