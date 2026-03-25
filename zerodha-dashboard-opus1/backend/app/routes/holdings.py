"""
Holdings endpoints.
"""
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.database import db
from app.models import Account, Holding, Snapshot
from app.services.portfolio_service import PortfolioService
from app.services.scheduler_service import SchedulerService
from app.services.us_holdings_service import USHoldingsService
from app.services.fd_service import FDService
import logging
import os

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


@holdings_bp.route('/us/upload', methods=['POST'])
def upload_us_holdings():
    """
    Upload US stock holdings from Excel file.

    Expects:
    - file: Excel file (.xlsx)
    - account_id: Account ID to associate holdings with (optional)

    Returns: Created holdings
    """
    try:
        # Check if file exists in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload Excel file (.xlsx)'}), 400

        # Get account_id from form data
        account_id = request.form.get('account_id')
        if not account_id:
            # Try to get first active account
            first_account = Account.query.filter_by(is_active=True).first()
            if not first_account:
                return jsonify({'error': 'No active account found. Please create an account first.'}), 400
            account_id = first_account.id
            logger.info(f"Using default account: {account_id}")

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', filename)
        file.save(temp_path)

        try:
            # Parse and create holdings
            service = USHoldingsService()
            parsed_holdings = service.parse_excel_file(temp_path)

            if not parsed_holdings:
                return jsonify({'error': 'No valid holdings found in file'}), 400

            # Create holdings with price fetching
            created_holdings = service.create_holdings(
                account_id=int(account_id),
                parsed_holdings=parsed_holdings,
                fetch_prices=True
            )

            return jsonify({
                'message': 'Holdings uploaded successfully',
                'count': len(created_holdings),
                'holdings': [
                    {
                        'symbol': h.tradingsymbol,
                        'quantity': h.quantity,
                        'current_value': float(h.current_value),
                        'pnl': float(h.pnl)
                    } for h in created_holdings
                ]
            }), 201
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error uploading US holdings: {e}")
        return jsonify({'error': str(e)}), 500


@holdings_bp.route('/us/refresh-prices', methods=['POST'])
def refresh_us_prices():
    """
    Refresh prices for US stock holdings.

    Expects:
    - account_id: Account ID (optional, refreshes all US holdings if not provided)

    Returns: Updated holdings
    """
    try:
        data = request.get_json() or {}
        account_id = data.get('account_id')

        # Get latest snapshot for US holdings
        query = Holding.query.filter_by(instrument_type='us_equity')
        if account_id:
            query = query.filter_by(account_id=account_id)

        # Get latest snapshot
        latest_snapshot = Snapshot.query.order_by(Snapshot.snapshot_date.desc()).first()
        if latest_snapshot:
            query = query.filter_by(snapshot_id=latest_snapshot.id)

        us_holdings = query.all()

        if not us_holdings:
            return jsonify({'message': 'No US holdings found'}), 200

        # Fetch fresh prices
        service = USHoldingsService()
        symbols = list(set([h.tradingsymbol for h in us_holdings]))  # Unique symbols
        prices = service.fetch_current_prices(symbols)

        # Update holdings
        updated_count = 0
        for holding in us_holdings:
            symbol = holding.tradingsymbol
            if symbol in prices and 'current_price' in prices[symbol]:
                price_data = prices[symbol]
                holding.last_price = price_data['current_price']
                holding.day_change = price_data.get('change', 0)
                holding.day_change_percentage = price_data.get('change_percent', 0)

                # Recalculate values
                holding.current_value = holding.quantity * holding.last_price
                investment = holding.quantity * holding.average_price
                holding.pnl = holding.current_value - investment
                holding.pnl_percentage = (holding.pnl / investment * 100) if investment > 0 else 0

                updated_count += 1

        db.session.commit()

        return jsonify({
            'message': 'Prices refreshed successfully',
            'updated_count': updated_count,
            'total_holdings': len(us_holdings)
        }), 200

    except Exception as e:
        logger.error(f"Error refreshing US prices: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@holdings_bp.route('/fd/upload', methods=['POST'])
def upload_fd_holdings():
    """
    Upload Fixed Deposit holdings from Excel file.

    Expects:
    - file: Excel file (.xlsx)
    - account_id: Account ID to associate FDs with (optional)

    Returns: Created FD holdings
    """
    try:
        # Check if file exists in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Validate file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload Excel file (.xlsx)'}), 400

        # Get account_id from form data
        account_id = request.form.get('account_id')
        if not account_id:
            # Try to get first active account
            first_account = Account.query.filter_by(is_active=True).first()
            if not first_account:
                return jsonify({'error': 'No active account found. Please create an account first.'}), 400
            account_id = first_account.id
            logger.info(f"Using default account: {account_id}")

        # Save file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join('/tmp', filename)
        file.save(temp_path)

        try:
            # Parse and create FD holdings
            service = FDService()
            parsed_fds = service.parse_excel_file(temp_path)

            if not parsed_fds:
                return jsonify({'error': 'No valid FD records found in file'}), 400

            # Create FD holdings with calculated returns
            created_holdings = service.create_fd_holdings(
                account_id=int(account_id),
                parsed_fds=parsed_fds
            )

            return jsonify({
                'message': 'Fixed deposits uploaded successfully',
                'count': len(created_holdings),
                'holdings': [
                    {
                        'bank_name': h.tradingsymbol,
                        'investment_amount': float(h.average_price),
                        'current_value': float(h.current_value),
                        'interest_earned': float(h.pnl),
                        'interest_rate': h.sector
                    } for h in created_holdings
                ]
            }), 201
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error uploading FD holdings: {e}")
        return jsonify({'error': str(e)}), 500


@holdings_bp.route('/fd/refresh-values', methods=['POST'])
def refresh_fd_values():
    """
    Recalculate interest for Fixed Deposit holdings.

    Expects:
    - account_id: Account ID (optional, refreshes all FDs if not provided)

    Returns: Updated FD count
    """
    try:
        data = request.get_json() or {}
        account_id = data.get('account_id')

        service = FDService()
        updated_count = service.refresh_fd_values(account_id)

        return jsonify({
            'message': 'FD values refreshed successfully',
            'updated_count': updated_count
        }), 200

    except Exception as e:
        logger.error(f"Error refreshing FD values: {e}")
        return jsonify({'error': str(e)}), 500
