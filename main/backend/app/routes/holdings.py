"""Authenticated portfolio holdings, synchronization, and import endpoints."""
import logging
import os
import tempfile
import zipfile

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from app.database import db
from app.models import Account
from app.services.eu_holdings_service import EUHoldingsService
from app.services.fd_service import FDService
from app.services.portfolio_service import PortfolioService
from app.services.us_holdings_service import USHoldingsService
from app.utils.auth import current_user_id, owned_account
from app.utils.rate_limiter import user_rate_limit


logger = logging.getLogger(__name__)
holdings_bp = Blueprint('holdings', __name__, url_prefix='/api/holdings')

ALLOWED_SPREADSHEETS = {
    '.xlsx': b'PK\x03\x04',
    '.xls': b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
}
MAX_XLSX_MEMBERS = 2000
MAX_XLSX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
SORT_FIELDS = {
    'tradingsymbol',
    'account_name',
    'quantity',
    'average_price',
    'last_price',
    'current_value',
    'pnl',
    'pnl_percentage',
    'day_change',
    'day_change_percentage',
}
INSTRUMENT_TYPES = {'equity', 'mf', 'us_equity', 'eu_equity', 'fd'}


def _selected_account(user_id, value, *, required=True):
    if value in (None, ''):
        if required:
            return None, (jsonify({'error': 'account_id is required'}), 400)
        return None, None
    try:
        account_id = int(value)
    except (TypeError, ValueError):
        return None, (jsonify({'error': 'account_id must be an integer'}), 400)
    account = owned_account(account_id, user_id=user_id, active_only=True)
    if not account:
        return None, (jsonify({'error': 'Account not found'}), 404)
    return account, None


def _refresh_accounts(user_id, value):
    if value in (None, ''):
        accounts = (
            Account.query.filter_by(user_id=user_id, is_active=True)
            .order_by(Account.id.asc())
            .all()
        )
        if not accounts:
            return [], (jsonify({'error': 'No active accounts found'}), 400)
        return accounts, None
    account, error = _selected_account(user_id, value)
    return ([account] if account else []), error


def _save_spreadsheet(upload):
    """Validate file signature and save to a random private temporary path."""
    filename = upload.filename or ''
    extension = os.path.splitext(filename)[1].lower()
    expected_magic = ALLOWED_SPREADSHEETS.get(extension)
    if expected_magic is None:
        raise ValueError('Upload an .xlsx or .xls spreadsheet')

    header = upload.stream.read(len(expected_magic))
    upload.stream.seek(0)
    if header != expected_magic:
        raise ValueError('Spreadsheet content does not match its extension')

    temporary = tempfile.NamedTemporaryFile(
        prefix='portfolio-import-',
        suffix=extension,
        delete=False,
    )
    path = temporary.name
    temporary.close()
    try:
        upload.save(path)
        if extension == '.xlsx':
            try:
                with zipfile.ZipFile(path) as archive:
                    members = archive.infolist()
                    expanded_size = sum(member.file_size for member in members)
                    if (
                        len(members) > MAX_XLSX_MEMBERS
                        or expanded_size > MAX_XLSX_UNCOMPRESSED_BYTES
                    ):
                        raise ValueError(
                            'Spreadsheet archive is too large to process safely'
                        )
            except zipfile.BadZipFile as error:
                raise ValueError('Spreadsheet archive is invalid') from error
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            logger.error("Failed to clean up rejected spreadsheet upload")
        raise
    return path


def _remove_spreadsheet(path):
    """Best-effort cleanup without turning a committed import into a false 500."""
    if not path or not os.path.exists(path):
        return
    try:
        os.unlink(path)
    except OSError:
        logger.error("Failed to clean up temporary spreadsheet upload")


@holdings_bp.get('')
@jwt_required()
def get_holdings():
    """Return current holdings across the user's latest account snapshots."""
    user_id = current_user_id()
    raw_account_id = request.args.get('account_id')
    try:
        account_id = int(raw_account_id) if raw_account_id is not None else None
    except ValueError:
        return jsonify({'error': 'account_id must be an integer'}), 400
    if account_id is not None and not owned_account(account_id, user_id=user_id):
        return jsonify({'error': 'Account not found'}), 404

    holdings = PortfolioService.get_latest_holdings(
        user_id,
        [account_id] if account_id is not None else None,
    )
    instrument_type = request.args.get('instrument_type')
    if instrument_type and instrument_type not in INSTRUMENT_TYPES:
        return jsonify({'error': 'Unsupported instrument_type'}), 400
    if instrument_type:
        holdings = [
            holding
            for holding in holdings
            if holding.instrument_type == instrument_type
        ]

    search = request.args.get('search', '').strip().casefold()
    if search:
        holdings = [
            holding
            for holding in holdings
            if search in holding.tradingsymbol.casefold()
            or search in holding.account.account_name.casefold()
        ]

    sort_by = request.args.get('sort_by', 'pnl_percentage')
    if sort_by not in SORT_FIELDS:
        return jsonify({'error': 'Unsupported sort field'}), 400
    sort_order = request.args.get('sort_order', 'desc').lower()
    if sort_order not in {'asc', 'desc'}:
        return jsonify({'error': 'sort_order must be asc or desc'}), 400
    descending = sort_order == 'desc'

    def sort_value(holding):
        if sort_by == 'account_name':
            return holding.account.account_name.casefold()
        value = getattr(holding, sort_by)
        if sort_by == 'tradingsymbol':
            return value.casefold()
        return float(value or 0)

    holdings.sort(key=sort_value, reverse=descending)
    return jsonify(
        {
            'holdings': [holding.to_dict() for holding in holdings],
            'summary': PortfolioService.calculate_portfolio_summary(holdings),
        }
    )


@holdings_bp.get('/aggregated')
@jwt_required()
def get_aggregated_holdings():
    return jsonify(PortfolioService.aggregate_accounts(current_user_id()))


@holdings_bp.post('/sync')
@jwt_required()
@user_rate_limit(max_requests=12, window_minutes=60)
def trigger_sync():
    user_id = current_user_id()
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON data'}), 400
    unexpected = sorted(set(data) - {'account_id'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400
    account_id = data.get('account_id')
    if account_id is not None:
        account, error = _selected_account(user_id, account_id)
        if error:
            return error
        account_id = account.id

    try:
        result = current_app.scheduler.trigger_manual_sync(
            user_id=user_id,
            account_id=account_id,
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception:
        logger.error('Manual sync failed for user %s', user_id)
        return jsonify({'error': 'Portfolio sync failed'}), 502


@holdings_bp.post('/us/upload')
@jwt_required()
@user_rate_limit(max_requests=10, window_minutes=60)
def upload_us_holdings():
    user_id = current_user_id()
    account, error = _selected_account(user_id, request.form.get('account_id'))
    if error:
        return error
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({'error': 'No file provided'}), 400

    path = None
    try:
        path = _save_spreadsheet(upload)
        service = USHoldingsService()
        parsed = service.parse_excel_file(path)
        created = service.create_holdings(account, parsed, fetch_prices=True)
        return jsonify(
            {
                'message': 'US holdings uploaded successfully',
                'count': len(created),
                'holdings': [holding.to_dict() for holding in created],
            }
        ), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400
    except Exception:
        db.session.rollback()
        logger.error('US holdings import failed for account %s', account.id)
        return jsonify({'error': 'Unable to import US holdings'}), 500
    finally:
        _remove_spreadsheet(path)


@holdings_bp.post('/us/refresh-prices')
@jwt_required()
@user_rate_limit(max_requests=20, window_minutes=60)
def refresh_us_prices():
    user_id = current_user_id()
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON data'}), 400
    unexpected = sorted(set(data) - {'account_id'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400
    accounts, error = _refresh_accounts(user_id, data.get('account_id'))
    if error:
        return error
    service = USHoldingsService()
    updated = succeeded = failed = skipped = 0
    for account in accounts:
        try:
            account_updates = service.refresh_prices(account)
            updated += account_updates
            if account_updates:
                succeeded += 1
            else:
                skipped += 1
        except Exception:
            db.session.rollback()
            failed += 1
            logger.error('US price refresh failed for account %s', account.id)
    if failed and not succeeded:
        status = 'failed'
    elif failed:
        status = 'partial'
    elif succeeded:
        status = 'completed'
    else:
        status = 'no_holdings'
    return jsonify(
        {
            'message': 'US price refresh finished',
            'updated_count': updated,
            'accounts_total': len(accounts),
            'accounts_succeeded': succeeded,
            'accounts_failed': failed,
            'accounts_skipped': skipped,
            'status': status,
        }
    ), (502 if status == 'failed' else 200)


@holdings_bp.post('/eu/upload')
@jwt_required()
@user_rate_limit(max_requests=10, window_minutes=60)
def upload_eu_holdings():
    user_id = current_user_id()
    account, error = _selected_account(user_id, request.form.get('account_id'))
    if error:
        return error
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({'error': 'No file provided'}), 400

    path = None
    try:
        path = _save_spreadsheet(upload)
        service = EUHoldingsService()
        parsed = service.parse_excel_file(path)
        created = service.create_holdings(account, parsed, fetch_prices=True)
        return jsonify(
            {
                'message': 'EU holdings uploaded successfully',
                'count': len(created),
                'holdings': [holding.to_dict() for holding in created],
            }
        ), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400
    except Exception:
        db.session.rollback()
        logger.error('EU holdings import failed for account %s', account.id)
        return jsonify({'error': 'Unable to import EU holdings'}), 500
    finally:
        _remove_spreadsheet(path)


@holdings_bp.post('/eu/refresh-prices')
@jwt_required()
@user_rate_limit(max_requests=20, window_minutes=60)
def refresh_eu_prices():
    user_id = current_user_id()
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON data'}), 400
    unexpected = sorted(set(data) - {'account_id'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400
    accounts, error = _refresh_accounts(user_id, data.get('account_id'))
    if error:
        return error
    service = EUHoldingsService()
    updated = succeeded = failed = skipped = 0
    for account in accounts:
        try:
            account_updates = service.refresh_prices(account)
            updated += account_updates
            if account_updates:
                succeeded += 1
            else:
                skipped += 1
        except Exception:
            db.session.rollback()
            failed += 1
            logger.error('EU price refresh failed for account %s', account.id)
    if failed and not succeeded:
        status = 'failed'
    elif failed:
        status = 'partial'
    elif succeeded:
        status = 'completed'
    else:
        status = 'no_holdings'
    return jsonify(
        {
            'message': 'EU price refresh finished',
            'updated_count': updated,
            'accounts_total': len(accounts),
            'accounts_succeeded': succeeded,
            'accounts_failed': failed,
            'accounts_skipped': skipped,
            'status': status,
        }
    ), (502 if status == 'failed' else 200)


@holdings_bp.post('/fd/upload')
@jwt_required()
@user_rate_limit(max_requests=10, window_minutes=60)
def upload_fd_holdings():
    user_id = current_user_id()
    account, error = _selected_account(user_id, request.form.get('account_id'))
    if error:
        return error
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({'error': 'No file provided'}), 400

    path = None
    try:
        path = _save_spreadsheet(upload)
        service = FDService()
        parsed = service.parse_excel_file(path)
        created = service.create_fd_holdings(account, parsed)
        return jsonify(
            {
                'message': 'Fixed deposits uploaded successfully',
                'count': len(created),
                'holdings': [holding.to_dict() for holding in created],
            }
        ), 201
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400
    except Exception:
        db.session.rollback()
        logger.error('FD import failed for account %s', account.id)
        return jsonify({'error': 'Unable to import fixed deposits'}), 500
    finally:
        _remove_spreadsheet(path)


@holdings_bp.post('/fd/refresh-values')
@jwt_required()
@user_rate_limit(max_requests=20, window_minutes=60)
def refresh_fd_values():
    user_id = current_user_id()
    data = request.get_json(silent=True)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON data'}), 400
    unexpected = sorted(set(data) - {'account_id'})
    if unexpected:
        return jsonify({'error': f'Unsupported field: {unexpected[0]}'}), 400
    accounts, error = _refresh_accounts(user_id, data.get('account_id'))
    if error:
        return error
    service = FDService()
    updated = succeeded = failed = 0
    for account in accounts:
        try:
            updated += service.refresh_fd_values(account)
            succeeded += 1
        except Exception:
            db.session.rollback()
            failed += 1
            logger.error('FD refresh failed for account %s', account.id)
    return jsonify(
        {
            'message': 'FD value refresh finished',
            'updated_count': updated,
            'accounts_succeeded': succeeded,
            'accounts_failed': failed,
            'status': 'completed' if failed == 0 else 'partial',
        }
    ), (200 if succeeded else 500)
