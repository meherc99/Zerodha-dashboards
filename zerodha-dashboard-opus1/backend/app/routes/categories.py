"""
Categories routes for transaction categorization.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.models.transaction_category import TransactionCategory
import logging

logger = logging.getLogger(__name__)

categories_bp = Blueprint('categories', __name__, url_prefix='/api')


@categories_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """
    Get all transaction categories.

    Returns:
        JSON response with list of categories
    """
    try:
        categories = TransactionCategory.query.order_by(
            TransactionCategory.parent_category_id.asc(),
            TransactionCategory.name.asc()
        ).all()

        return jsonify([cat.to_dict() for cat in categories]), 200

    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        return jsonify({'error': 'Failed to fetch categories'}), 500
