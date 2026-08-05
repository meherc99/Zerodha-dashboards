"""Authenticated portfolio analytics endpoints."""
from datetime import datetime, timedelta, timezone
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.services.analytics_service import AnalyticsService
from app.services.portfolio_service import PortfolioService
from app.utils.auth import current_user_id, owned_account


logger = logging.getLogger(__name__)
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


def _account_filter(user_id):
    raw_account_id = request.args.get('account_id')
    try:
        account_id = int(raw_account_id) if raw_account_id is not None else None
    except ValueError:
        return None, (jsonify({'error': 'account_id must be an integer'}), 400)
    if account_id is not None and not owned_account(account_id, user_id=user_id):
        return None, (jsonify({'error': 'Account not found'}), 404)
    return account_id, None


def _parse_datetime(value, default):
    if not value:
        return default
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


@analytics_bp.get('/portfolio-value-history')
@jwt_required()
def get_portfolio_history():
    user_id = current_user_id()
    account_id, error = _account_filter(user_id)
    if error:
        return error

    granularity = request.args.get('granularity', 'daily')
    if granularity not in {'daily', 'weekly', 'monthly'}:
        return jsonify({'error': 'Invalid granularity'}), 400
    currency = request.args.get('currency')
    if currency:
        currency = currency.upper()

    try:
        end_date = _parse_datetime(request.args.get('end_date'), datetime.utcnow())
        start_date = _parse_datetime(
            request.args.get('start_date'),
            end_date - timedelta(days=30),
        )
    except ValueError:
        return jsonify({'error': 'Dates must be ISO-8601 values'}), 400
    if start_date > end_date:
        return jsonify({'error': 'start_date must not be after end_date'}), 400

    timeseries = AnalyticsService.get_portfolio_history(
        user_id=user_id,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        currency=currency,
    )
    return jsonify(
        {
            'timeseries': timeseries,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'currency': currency,
            'data_points': len(timeseries),
        }
    )


@analytics_bp.get('/sector-breakdown')
@jwt_required()
def get_sector_breakdown():
    user_id = current_user_id()
    account_id, error = _account_filter(user_id)
    if error:
        return error
    holdings = PortfolioService.get_latest_holdings(
        user_id,
        [account_id] if account_id is not None else None,
    )
    return jsonify(
        {'sectors': PortfolioService.calculate_sector_breakdown(holdings)}
    )


@analytics_bp.get('/performance-metrics')
@jwt_required()
def get_performance_metrics():
    user_id = current_user_id()
    account_id, error = _account_filter(user_id)
    if error:
        return error
    period_days = request.args.get('period_days', default=30, type=int)
    if period_days is None or not 1 <= period_days <= 3650:
        return jsonify({'error': 'period_days must be between 1 and 3650'}), 400
    currency = request.args.get('currency')
    if currency:
        currency = currency.upper()

    metrics = AnalyticsService.get_performance_metrics(
        user_id=user_id,
        account_id=account_id,
        period_days=period_days,
        currency=currency,
    )
    holdings = PortfolioService.get_latest_holdings(
        user_id,
        [account_id] if account_id is not None else None,
    )
    if currency:
        holdings = [
            holding
            for holding in holdings
            if (holding.currency or 'INR').upper() == currency
        ]
    metrics['top_performers'] = PortfolioService.get_top_performers(holdings, 5)
    metrics['worst_performers'] = PortfolioService.get_worst_performers(
        holdings, 5
    )
    return jsonify(metrics)


@analytics_bp.get('/correlation-matrix')
@jwt_required()
def get_correlation_matrix():
    current_user_id()
    symbols = [
        symbol.strip().upper()
        for symbol in request.args.get('symbols', '').split(',')
        if symbol.strip()
    ]
    if len(symbols) < 2 or len(symbols) > 50:
        return jsonify({'error': 'Provide between 2 and 50 symbols'}), 400
    period_days = request.args.get('period', default=90, type=int)
    if period_days is None or not 2 <= period_days <= 3650:
        return jsonify({'error': 'period must be between 2 and 3650 days'}), 400
    return jsonify(
        AnalyticsService.calculate_correlation_matrix(symbols, period_days)
    )


@analytics_bp.get('/heatmap')
@jwt_required()
def get_heatmap():
    user_id = current_user_id()
    account_id, error = _account_filter(user_id)
    if error:
        return error
    metric = request.args.get('metric', 'pnl_percentage')
    if metric not in {'pnl_percentage', 'day_change_percentage'}:
        return jsonify({'error': 'Invalid heatmap metric'}), 400
    period = request.args.get('period', 'week')
    if period not in {'week', 'month', 'quarter', 'year'}:
        return jsonify({'error': 'Invalid heatmap period'}), 400

    holdings = PortfolioService.get_latest_holdings(
        user_id,
        [account_id] if account_id is not None else None,
    )
    return jsonify(
        {
            'data': AnalyticsService.generate_heatmap_data(
                holdings,
                metric=metric,
                period=period,
            )
        }
    )
