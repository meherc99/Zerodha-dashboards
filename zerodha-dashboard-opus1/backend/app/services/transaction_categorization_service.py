"""
Transaction Categorization Service for auto-categorizing transactions using keywords.
"""
import logging
from typing import Tuple, List, Dict, Optional
from decimal import Decimal
from app.models.transaction_category import TransactionCategory

logger = logging.getLogger(__name__)


class TransactionCategorizationService:
    """Service for categorizing transactions using keyword matching"""

    @staticmethod
    def auto_categorize(description: str, amount: Decimal) -> Tuple[Optional[int], float]:
        """
        Auto-categorize a transaction based on description keywords.

        Args:
            description: Transaction description
            amount: Transaction amount (currently not used, but available for future logic)

        Returns:
            Tuple of (category_id, confidence)
            - category_id: ID of matched category or Uncategorized
            - confidence: 0.8 for keyword match, 0.5 for Uncategorized
        """
        if not description:
            # Return Uncategorized
            uncategorized = TransactionCategory.query.filter_by(name='Uncategorized').first()
            if uncategorized:
                return uncategorized.id, 0.5
            return None, 0.5

        # Normalize description for matching
        description_lower = description.lower().strip()

        # Get all categories with keywords
        categories = TransactionCategory.query.filter(
            TransactionCategory.keywords.isnot(None)
        ).all()

        # Try to match keywords
        for category in categories:
            if not category.keywords:
                continue

            # Check each keyword
            for keyword in category.keywords:
                keyword_lower = keyword.lower().strip()

                # Check if keyword is in description
                if keyword_lower in description_lower:
                    logger.info(
                        f"Matched category '{category.name}' for description '{description}' "
                        f"using keyword '{keyword}'"
                    )
                    return category.id, 0.8

        # No match found - return Uncategorized
        uncategorized = TransactionCategory.query.filter_by(name='Uncategorized').first()
        if uncategorized:
            logger.info(f"No category match for description '{description}', using Uncategorized")
            return uncategorized.id, 0.5

        # Fallback if Uncategorized category doesn't exist
        logger.warning("Uncategorized category not found in database")
        return None, 0.5

    @staticmethod
    def bulk_categorize(transactions: List[Dict]) -> List[Dict]:
        """
        Categorize a list of transactions.

        Args:
            transactions: List of transaction dicts with 'description' and 'amount' fields

        Returns:
            List of transactions with added 'category_id' and 'category_confidence' fields
        """
        categorized_transactions = []

        for txn in transactions:
            # Make a copy to avoid modifying original
            categorized_txn = dict(txn)

            # Get description and amount
            description = txn.get('description', '')
            amount = txn.get('amount', Decimal('0'))

            # Categorize
            category_id, confidence = TransactionCategorizationService.auto_categorize(
                description, amount
            )

            # Add category fields
            categorized_txn['category_id'] = category_id
            categorized_txn['category_confidence'] = confidence

            categorized_transactions.append(categorized_txn)

        logger.info(f"Categorized {len(categorized_transactions)} transactions")

        return categorized_transactions
