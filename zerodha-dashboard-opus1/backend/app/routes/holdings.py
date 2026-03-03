"""
Holdings endpoints.
"""
from flask import Blueprint, request, jsonify
from app.database import db
from app.models import Account, Holding, Snapshot
from app.services.portfolio_service import PortfolioService
from app.services.scheduler_service import SchedulerService
import logging

logger = logging.getLogger(__name__)

holdings_bp = Blueprint('holdings', __name__, url_prefix='/api/holdings')


@holdings_bp.route('', methods=['GET'])
def get_holdings():
    """Get holdings with optional filtering"""
    # Query parameters
    account_id = request.args.get('account_id', type=int)
    instrument_type = request.args.get('instrument_type')
    sort_by = request.args.get('sort_by', 'pnl_percentage')
    sort_order = request.args.get('sort_order', 'desc')

    try:
        # Get latest snapshot
        latest_snapshot = Snapshot.query.order_by(Snapshot.snapshot_date.desc()).first()

        if not latest_snapshot:
            return jsonify({
                'holdings': [],
                'summary': {
                    'total_holdings': 0,
                    'total_investment': 0,
                    'current_value': 0,
                    'total_pnl': 0,
                    'total_pnl_percentage': 0,
                    'day_change': 0
                }
            }), 200

        # Build query
        query = Holding.query.filter_by(snapshot_id=latest_snapshot.id)

        if account_id:
            query = query.filter_by(account_id=account_id)

        if instrument_type:
            query = query.filter_by(instrument_type=instrument_type)

        # Apply sorting
        if sort_by in ['pnl', 'pnl_percentage', 'current_value', 'tradingsymbol']:
            sort_column = getattr(Holding, sort_by)
            if sort_order == 'desc':
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

        holdings = query.all()

        # Calculate summary
        summary = PortfolioService.calculate_portfolio_summary(holdings)

        return jsonify({
            'holdings': [h.to_dict() for h in holdings],
            'summary': summary
        }), 200

    except Exception as e:
        logger.error(f"Error fetching holdings: {e}")
        return jsonify({'error': 'Failed to fetch holdings'}), 500


@holdings_bp.route('/aggregated', methods=['GET'])
def get_aggregated_holdings():
    """Get aggregated holdings across all family accounts"""
    try:
        aggregated = PortfolioService.aggregate_accounts()

        return jsonify(aggregated), 200

    except Exception as e:
        logger.error(f"Error fetching aggregated holdings: {e}")
        return jsonify({'error': 'Failed to fetch aggregated holdings'}), 500


@holdings_bp.route('/sync', methods=['POST'])
def trigger_sync():
    """Trigger manual sync for specific account or all accounts"""
    data = request.get_json() or {}
    account_id = data.get('account_id')

    try:
        # Get scheduler instance from app context
        from flask import current_app
        scheduler = current_app.scheduler

        scheduler.trigger_manual_sync(account_id=account_id)

        return jsonify({
            'message': 'Sync initiated successfully',
            'account_id': account_id
        }), 202

    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        return jsonify({'error': str(e)}), 500
