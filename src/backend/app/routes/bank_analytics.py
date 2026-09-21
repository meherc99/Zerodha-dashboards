"""
Bank Analytics Routes for spending patterns and cashflow analysis.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import math
from app.services.bank_analytics_service import BankAnalyticsService
from app.utils.rate_limiter import user_rate_limit

bank_analytics_bp = Blueprint('bank_analytics', __name__)


def _reject_unknown_query_fields(*allowed):
    unexpected = sorted(set(request.args) - set(allowed))
    if unexpected:
        return jsonify({
            'error': f'Unsupported query parameter: {unexpected[0]}'
        })
    return None


def _bounded_integer(name, default, minimum, maximum):
    raw_value = request.args.get(name)
    if raw_value is None:
        return default, None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None, jsonify({'error': f'{name} must be an integer'})
    if not minimum <= value <= maximum:
        return None, jsonify({
            'error': f'{name} must be between {minimum} and {maximum}'
        })
    return value, None


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/balance-trend', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_balance_trend(bank_account_id):
    """
    Get balance trend over time.

    Query params:
        days (int): Number of days to analyze (default: 30)

    Returns:
        200: {dates: [...], balances: [...], period_days: 30}
        404: Account not found or not owned by user
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('days')
    if unknown:
        return unknown, 400
    days, error = _bounded_integer('days', 30, 1, 3650)
    if error:
        return error, 400

    result = BankAnalyticsService.get_balance_trend(bank_account_id, days, user_id)

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/category-breakdown', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_category_breakdown(bank_account_id):
    """
    Get spending breakdown by category (debits only).

    Query params:
        period_days (int): Number of days to analyze (default: 30)

    Returns:
        200: {categories: [...], total_spending: 58800.00, period_days: 30}
        404: Account not found or not owned by user
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('period_days')
    if unknown:
        return unknown, 400
    period_days, error = _bounded_integer('period_days', 30, 1, 3650)
    if error:
        return error, 400

    result = BankAnalyticsService.get_category_breakdown(
        bank_account_id, period_days, user_id
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/cashflow', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_cashflow_analysis(bank_account_id):
    """
    Get cashflow analysis (credits vs debits over time).

    Query params:
        period_days (int): Number of days to analyze (default: 30)

    Returns:
        200: {periods: [...], credits: [...], debits: [...], net: [...], period_days: 30}
        404: Account not found or not owned by user
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('period_days')
    if unknown:
        return unknown, 400
    period_days, error = _bounded_integer('period_days', 30, 1, 3650)
    if error:
        return error, 400

    result = BankAnalyticsService.get_cashflow_analysis(
        bank_account_id, period_days, user_id
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/monthly-cashflow', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_monthly_cashflow(bank_account_id):
    """
    Get monthly income vs expenses analysis.

    Query params:
        num_months (int): Number of calendar months to return (default: 12)

    Returns:
        200: {months: [...], income: [...], expenses: [...], net: [...], num_months: 12}
        404: Account not found or not owned by user
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('num_months')
    if unknown:
        return unknown, 400
    num_months, error = _bounded_integer('num_months', 12, 1, 60)
    if error:
        return error, 400

    result = BankAnalyticsService.get_monthly_cashflow(
        bank_account_id, num_months, user_id
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/top-merchants', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_top_merchants(bank_account_id):
    """
    Get top spending merchants.

    Query params:
        limit (int): Number of top merchants to return (default: 10)
        period_days (int): Number of days to analyze (default: 30)

    Returns:
        200: {merchants: [{merchant, total, count, avg_transaction}, ...], limit: 10}
        404: Account not found or not owned by user
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('limit', 'period_days')
    if unknown:
        return unknown, 400
    limit, error = _bounded_integer('limit', 10, 1, 100)
    if error:
        return error, 400
    period_days, error = _bounded_integer(
        'period_days',
        30,
        1,
        3650,
    )
    if error:
        return error, 400

    result = BankAnalyticsService.get_top_merchants(
        bank_account_id,
        limit,
        user_id,
        period_days=period_days,
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/anomalies', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_anomalies(bank_account_id):
    """
    Detect unusual transactions based on statistical analysis.

    Query params:
        threshold (float): Number of standard deviations for detection (default: 2.0)

    Returns:
        200: {anomalies: [...], statistics: {...}, threshold: 2.0}
        404: Account not found or not owned by user
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('threshold')
    if unknown:
        return unknown, 400
    raw_threshold = request.args.get('threshold', '2.0')
    try:
        threshold = float(raw_threshold)
    except (TypeError, ValueError):
        return jsonify({'error': 'Threshold must be numeric'}), 400

    # Validate threshold
    if not math.isfinite(threshold) or not 0 < threshold <= 10:
        return jsonify({
            'error': 'Threshold must be between 0 and 10'
        }), 400

    result = BankAnalyticsService.detect_anomalies(
        bank_account_id, user_id, threshold
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/predictions', methods=['GET'])
@jwt_required()
@user_rate_limit(max_requests=120, window_minutes=60)
def get_spending_predictions(bank_account_id):
    """
    Predict future spending and balance based on historical trends.

    Query params:
        forecast_days (int): Number of days to forecast (default: 30, max: 90)

    Returns:
        200: {predictions: [...], current_balance: ..., statistics: {...}}
        404: Account not found or not owned by user
        400: Invalid forecast_days
    """
    user_id = int(get_jwt_identity())
    unknown = _reject_unknown_query_fields('forecast_days')
    if unknown:
        return unknown, 400
    forecast_days = request.args.get('forecast_days', default=30, type=int)

    # Validate forecast_days
    if forecast_days <= 0 or forecast_days > 90:
        return jsonify({'error': 'forecast_days must be between 1 and 90'}), 400

    result = BankAnalyticsService.predict_spending(
        bank_account_id, user_id, forecast_days
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200
