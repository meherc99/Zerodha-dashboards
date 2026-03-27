"""
Bank Analytics Routes for spending patterns and cashflow analysis.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.bank_analytics_service import BankAnalyticsService

bank_analytics_bp = Blueprint('bank_analytics', __name__)


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/balance-trend', methods=['GET'])
@jwt_required()
def get_balance_trend(bank_account_id):
    """
    Get balance trend over time.

    Query params:
        days (int): Number of days to analyze (default: 30)

    Returns:
        200: {dates: [...], balances: [...], period_days: 30}
        404: Account not found or not owned by user
    """
    user_id = get_jwt_identity()
    days = request.args.get('days', default=30, type=int)

    result = BankAnalyticsService.get_balance_trend(bank_account_id, days, user_id)

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/category-breakdown', methods=['GET'])
@jwt_required()
def get_category_breakdown(bank_account_id):
    """
    Get spending breakdown by category (debits only).

    Query params:
        period_days (int): Number of days to analyze (default: 30)

    Returns:
        200: {categories: [...], total_spending: 58800.00, period_days: 30}
        404: Account not found or not owned by user
    """
    user_id = get_jwt_identity()
    period_days = request.args.get('period_days', default=30, type=int)

    result = BankAnalyticsService.get_category_breakdown(
        bank_account_id, period_days, user_id
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/cashflow', methods=['GET'])
@jwt_required()
def get_cashflow_analysis(bank_account_id):
    """
    Get cashflow analysis (credits vs debits over time).

    Query params:
        period_days (int): Number of days to analyze (default: 30)

    Returns:
        200: {periods: [...], credits: [...], debits: [...], net: [...], period_days: 30}
        404: Account not found or not owned by user
    """
    user_id = get_jwt_identity()
    period_days = request.args.get('period_days', default=30, type=int)

    result = BankAnalyticsService.get_cashflow_analysis(
        bank_account_id, period_days, user_id
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200


@bank_analytics_bp.route('/bank-accounts/<int:bank_account_id>/analytics/top-merchants', methods=['GET'])
@jwt_required()
def get_top_merchants(bank_account_id):
    """
    Get top spending merchants.

    Query params:
        limit (int): Number of top merchants to return (default: 10)

    Returns:
        200: {merchants: [{merchant, total, count, avg_transaction}, ...], limit: 10}
        404: Account not found or not owned by user
    """
    user_id = get_jwt_identity()
    limit = request.args.get('limit', default=10, type=int)

    result = BankAnalyticsService.get_top_merchants(
        bank_account_id, limit, user_id
    )

    if result is None:
        return jsonify({'error': 'Bank account not found'}), 404

    return jsonify(result), 200
