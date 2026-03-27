"""
Transaction Categorization Service for auto-categorizing transactions using keywords.
"""
import logging
import re
from typing import Tuple, List, Dict, Optional
from decimal import Decimal
from app.database import db
from app.models.transaction_category import TransactionCategory
from app.models.transaction import Transaction

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

    @staticmethod
    def learn_from_user_correction(transaction_id: int, new_category_id: int):
        """
        Learn from user's category correction and update category keywords.

        When a user changes a transaction's category, we extract meaningful
        keywords from the description and add them to the new category.
        We also update similar uncategorized transactions.

        Args:
            transaction_id: ID of the transaction that was recategorized
            new_category_id: ID of the new category

        Raises:
            ValueError: If transaction or category not found
        """
        # Get transaction
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            raise ValueError(f"Transaction not found: {transaction_id}")

        # Get new category
        new_category = TransactionCategory.query.get(new_category_id)
        if not new_category:
            raise ValueError(f"Category not found: {new_category_id}")

        # Extract meaningful keywords from description
        keywords = TransactionCategorizationService._extract_keywords(
            transaction.description
        )

        if not keywords:
            logger.info(f"No keywords extracted from '{transaction.description}'")
            return

        # Get existing keywords for category
        existing_keywords = new_category.keywords or []

        # Add new keywords that aren't already present
        new_keywords_added = []
        for keyword in keywords:
            if keyword not in existing_keywords:
                existing_keywords.append(keyword)
                new_keywords_added.append(keyword)

        if new_keywords_added:
            # Update category keywords
            new_category.keywords = existing_keywords
            db.session.commit()

            logger.info(
                f"Added keywords {new_keywords_added} to category '{new_category.name}' "
                f"from transaction '{transaction.description}'"
            )

            # Update similar uncategorized transactions
            TransactionCategorizationService._update_similar_transactions(
                transaction.bank_account_id,
                transaction.description,
                new_category_id
            )

    @staticmethod
    def _extract_keywords(description: str) -> List[str]:
        """
        Extract meaningful keywords from transaction description.

        Removes common words, numbers, and extracts merchant names or key terms.

        Args:
            description: Transaction description

        Returns:
            List of extracted keywords (lowercase)
        """
        if not description:
            return []

        # Common stop words to ignore
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'upi', 'txn', 'tran',
            'transaction', 'payment', 'purchase', 'ref', 'reference', 'no',
            'date', 'time', 'amt', 'amount', 'debit', 'credit', 'card'
        }

        # Clean description
        description_lower = description.lower()

        # Remove special characters and split into words
        words = re.findall(r'\b[a-z]{3,}\b', description_lower)

        # Filter out stop words and extract meaningful keywords
        keywords = []
        for word in words:
            if word not in stop_words and len(word) >= 3:
                keywords.append(word)

        # Limit to 3 most significant keywords (longer words tend to be more specific)
        keywords.sort(key=len, reverse=True)
        return keywords[:3]

    @staticmethod
    def _update_similar_transactions(bank_account_id: int, description: str,
                                     category_id: int):
        """
        Update similar uncategorized transactions with the new category.

        Args:
            bank_account_id: ID of the bank account
            description: Original transaction description
            category_id: Category ID to apply
        """
        # Extract keywords from description
        keywords = TransactionCategorizationService._extract_keywords(description)
        if not keywords:
            return

        # Get uncategorized category ID
        uncategorized = TransactionCategory.query.filter_by(name='Uncategorized').first()
        if not uncategorized:
            return

        # Find similar uncategorized transactions
        # Look for transactions with matching keywords in the same account
        similar_transactions = Transaction.query.filter(
            Transaction.bank_account_id == bank_account_id,
            Transaction.category_id == uncategorized.id,
            Transaction.verified == False
        ).all()

        updated_count = 0
        for txn in similar_transactions:
            if not txn.description:
                continue

            # Check if any keyword matches
            txn_desc_lower = txn.description.lower()
            if any(keyword in txn_desc_lower for keyword in keywords):
                txn.category_id = category_id
                txn.category_confidence = 0.7  # Lower confidence for auto-update
                updated_count += 1

        if updated_count > 0:
            db.session.commit()
            logger.info(
                f"Updated {updated_count} similar transactions to category {category_id}"
            )
