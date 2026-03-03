"""
Analytics endpoints.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.models import Holding, Snapshot
from app.services.analytics_service import AnalyticsService
from app.services.portfolio_service import PortfolioService
import logging

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@analytics_bp.route('/portfolio-value-history', methods=['GET'])
def get_portfolio_history():
    """Get historical portfolio value"""
    # Query parameters
    account_id = request.args.get('account_id', type=int)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    granularity = request.args.get('granularity', 'daily')

    try:
        # Parse dates
        end_date = datetime.utcnow()
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))

        start_date = end_date - timedelta(days=30)
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))

        # Get timeseries data
        timeseries = AnalyticsService.get_portfolio_history(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )

        return jsonify({
            'timeseries': timeseries,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'data_points': len(timeseries)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching portfolio history: {e}")
        return jsonify({'error': 'Failed to fetch portfolio history'}), 500


@analytics_bp.route('/sector-breakdown', methods=['GET'])
def get_sector_breakdown():
    """Get sector-wise allocation and performance"""
    account_id = request.args.get('account_id', type=int)

    try:
        # Get latest snapshot
        latest_snapshot = Snapshot.query.order_by(Snapshot.snapshot_date.desc()).first()

        if not latest_snapshot:
            return jsonify({'sectors': []}), 200

        # Build query
        query = Holding.query.filter_by(snapshot_id=latest_snapshot.id)

        if account_id:
            query = query.filter_by(account_id=account_id)

        holdings = query.all()

        # Calculate sector breakdown
        sectors = PortfolioService.calculate_sector_breakdown(holdings)

        return jsonify({'sectors': sectors}), 200

    except Exception as e:
        logger.error(f"Error fetching sector breakdown: {e}")
        return jsonify({'error': 'Failed to fetch sector breakdown'}), 500


@analytics_bp.route('/performance-metrics', methods=['GET'])
def get_performance_metrics():
    """Get advanced performance metrics"""
    account_id = request.args.get('account_id', type=int)
    period_days = request.args.get('period_days', default=30, type=int)

    try:
        metrics = AnalyticsService.get_performance_metrics(
            account_id=account_id,
            period_days=period_days
        )

        # Get top and worst performers
        latest_snapshot = Snapshot.query.order_by(Snapshot.snapshot_date.desc()).first()

        if latest_snapshot:
            query = Holding.query.filter_by(snapshot_id=latest_snapshot.id)

            if account_id:
                query = query.filter_by(account_id=account_id)

            holdings = query.all()

            metrics['top_performers'] = PortfolioService.get_top_performers(holdings, limit=5)
            metrics['worst_performers'] = PortfolioService.get_worst_performers(holdings, limit=5)

        return jsonify(metrics), 200

    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        return jsonify({'error': 'Failed to fetch performance metrics'}), 500


@analytics_bp.route('/correlation-matrix', methods=['GET'])
def get_correlation_matrix():
    """Get correlation matrix for stocks"""
    symbols_str = request.args.get('symbols', '')
    period_days = request.args.get('period', default=90, type=int)

    if not symbols_str:
        return jsonify({'error': 'Symbols parameter required'}), 400

    try:
        symbols = [s.strip() for s in symbols_str.split(',')]

        correlation_data = AnalyticsService.calculate_correlation_matrix(
            symbols=symbols,
            period_days=period_days
        )

        return jsonify(correlation_data), 200

    except Exception as e:
        logger.error(f"Error calculating correlation matrix: {e}")
        return jsonify({'error': 'Failed to calculate correlation matrix'}), 500


@analytics_bp.route('/heatmap', methods=['GET'])
def get_heatmap():
    """Get performance heatmap data"""
    metric = request.args.get('metric', 'pnl_percentage')
    period = request.args.get('period', 'week')

    try:
        # Get latest holdings
        latest_snapshot = Snapshot.query.order_by(Snapshot.snapshot_date.desc()).first()

        if not latest_snapshot:
            return jsonify({'data': []}), 200

        holdings = Holding.query.filter_by(snapshot_id=latest_snapshot.id).all()

        heatmap_data = AnalyticsService.generate_heatmap_data(
            holdings=holdings,
            metric=metric,
            period=period
        )

        return jsonify({'data': heatmap_data}), 200

    except Exception as e:
        logger.error(f"Error generating heatmap: {e}")
        return jsonify({'error': 'Failed to generate heatmap'}), 500
