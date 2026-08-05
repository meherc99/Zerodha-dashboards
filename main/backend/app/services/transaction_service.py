"""
Transaction service for managing and querying bank transactions.
"""
from datetime import datetime
import logging

from sqlalchemy import or_, and_
from app.database import db
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.models.bank_account import BankAccount


logger = logging.getLogger(__name__)


class TransactionService:
    """Service for transaction management and queries"""

    @staticmethod
    def _apply_filters(query, filters):
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(
                    filters['date_from'],
                    '%Y-%m-%d',
                ).date()
            except (TypeError, ValueError):
                raise ValueError(
                    'Invalid date_from format. Use YYYY-MM-DD'
                ) from None
            query = query.filter(Transaction.transaction_date >= date_from)

        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(
                    filters['date_to'],
                    '%Y-%m-%d',
                ).date()
            except (TypeError, ValueError):
                raise ValueError(
                    'Invalid date_to format. Use YYYY-MM-DD'
                ) from None
            query = query.filter(Transaction.transaction_date <= date_to)

        transaction_type = filters.get('type', 'all')
        if transaction_type not in {'all', 'credit', 'debit'}:
            raise ValueError("Type must be 'credit', 'debit', or 'all'")
        if transaction_type != 'all':
            query = query.filter(
                Transaction.transaction_type == transaction_type
            )

        if filters.get('category_id') not in (None, ''):
            try:
                category_id = int(filters['category_id'])
            except (TypeError, ValueError):
                raise ValueError('category_id must be an integer') from None
            if category_id <= 0:
                raise ValueError('category_id must be a positive integer')
            query = query.filter(Transaction.category_id == category_id)

        search = filters.get('search')
        if search:
            if not isinstance(search, str) or len(search) > 200:
                raise ValueError('search must contain at most 200 characters')
            query = query.filter(Transaction.description.ilike(f'%{search}%'))

        return query

    @staticmethod
    def _sort_and_paginate(query, filters):
        sort_columns = {
            'date': Transaction.transaction_date,
            'amount': Transaction.amount,
            'description': Transaction.description,
        }
        sort_by = filters.get('sort_by', 'date')
        if sort_by not in sort_columns:
            raise ValueError('sort_by must be date, amount, or description')
        order = filters.get('order', 'desc')
        if order not in {'asc', 'desc'}:
            raise ValueError('order must be asc or desc')
        sort_column = sort_columns[sort_by]
        query = query.order_by(
            sort_column.asc() if order == 'asc' else sort_column.desc(),
            Transaction.id.asc(),
        )

        try:
            page = int(filters.get('page', 1))
            limit = int(filters.get('limit', 50))
        except (TypeError, ValueError):
            raise ValueError('page and limit must be integers') from None
        if not 1 <= page <= 1_000_000:
            raise ValueError('page must be between 1 and 1000000')
        if not 1 <= limit <= 200:
            raise ValueError('limit must be between 1 and 200')
        return query.offset((page - 1) * limit).limit(limit), page, limit

    @staticmethod
    def list_transactions(bank_account_id, filters, user_id):
        """
        List transactions for a specific bank account with filters and pagination.

        Args:
            bank_account_id: ID of the bank account
            filters: Dict with optional keys:
                - date_from (str): Start date (YYYY-MM-DD)
                - date_to (str): End date (YYYY-MM-DD)
                - type (str): 'credit', 'debit', or 'all'
                - category_id (int): Filter by category
                - search (str): Search in description
                - sort_by (str): 'date', 'amount', 'description'
                - order (str): 'asc' or 'desc'
                - page (int): Page number (default 1)
                - limit (int): Results per page (default 50, max 200)
            user_id: ID of the user making the request

        Returns:
            Dict with:
                - transactions: List of transaction dicts
                - total: Total count
                - page: Current page
                - limit: Results per page
                - pages: Total pages

        Raises:
            ValueError: If bank account not found or user doesn't own it
        """
        # Verify bank account exists
        bank_account = BankAccount.query.filter_by(
            id=bank_account_id,
            is_active=True,
        ).first()

        if not bank_account:
            raise ValueError("Bank account not found")

        # Verify ownership
        if bank_account.user_id != user_id:
            raise ValueError("Access denied")

        # Build base query
        query = Transaction.query.filter_by(bank_account_id=bank_account_id)

        query = TransactionService._apply_filters(query, filters)

        # Get total count before pagination
        total = query.count()

        query, page, limit = TransactionService._sort_and_paginate(
            query,
            filters,
        )
        transactions = query.all()

        # Calculate total pages
        pages = (total + limit - 1) // limit if total > 0 else 0

        # Convert to dicts with category info
        transaction_dicts = []
        for txn in transactions:
            txn_dict = txn.to_dict()

            # Add category info
            if txn.category and txn.category.is_system:
                txn_dict['category'] = txn.category.to_dict()
            else:
                txn_dict['category_id'] = None
                txn_dict['category'] = None

            transaction_dicts.append(txn_dict)

        return {
            'transactions': transaction_dicts,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': pages
        }

    @staticmethod
    def search_all_transactions(filters, user_id):
        """
        Search transactions across all user's bank accounts.

        Args:
            filters: Same as list_transactions
            user_id: ID of the user making the request

        Returns:
            Dict with transactions list and metadata
        """
        # Build base query joining bank accounts to filter by user
        query = Transaction.query.join(BankAccount).filter(
            BankAccount.user_id == user_id,
            BankAccount.is_active.is_(True),
        )

        query = TransactionService._apply_filters(query, filters)

        # Get total count before pagination
        total = query.count()

        query, page, limit = TransactionService._sort_and_paginate(
            query,
            filters,
        )
        transactions = query.all()

        # Calculate total pages
        pages = (total + limit - 1) // limit if total > 0 else 0

        # Convert to dicts with category and bank account info
        transaction_dicts = []
        for txn in transactions:
            txn_dict = txn.to_dict()

            # Add category info
            if txn.category and txn.category.is_system:
                txn_dict['category'] = txn.category.to_dict()
            else:
                txn_dict['category_id'] = None
                txn_dict['category'] = None

            # Add bank account info
            txn_dict['bank_account'] = {
                'id': txn.bank_account.id,
                'bank_name': txn.bank_account.bank_name
            }

            transaction_dicts.append(txn_dict)

        return {
            'transactions': transaction_dicts,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': pages
        }

    @staticmethod
    def update_transaction(transaction_id, data, user_id):
        """
        Update a transaction. Only allows updating category, notes, and verified status.

        Args:
            transaction_id: ID of the transaction
            data: Dict with fields to update (category_id, notes, verified)
            user_id: ID of the user making the request

        Returns:
            Updated transaction dict

        Raises:
            ValueError: If transaction not found, access denied, or invalid data
        """
        if not isinstance(data, dict) or not data:
            raise ValueError('Update data must be a non-empty object')
        unexpected = sorted(set(data) - {'category_id', 'notes', 'verified'})
        if unexpected:
            raise ValueError(f'Unsupported field: {unexpected[0]}')

        category_id = data.get('category_id')
        if 'category_id' in data and category_id is not None and (
            isinstance(category_id, bool)
            or not isinstance(category_id, int)
            or category_id <= 0
        ):
            raise ValueError(
                'category_id must be a positive integer or null'
            )
        notes = data.get('notes')
        if 'notes' in data and notes is not None and (
            not isinstance(notes, str) or len(notes) > 1000
        ):
            raise ValueError(
                'notes must contain at most 1000 characters or be null'
            )
        if 'verified' in data and not isinstance(data['verified'], bool):
            raise ValueError('verified must be a boolean')

        # Check if transaction exists
        transaction = Transaction.query.filter_by(id=transaction_id).first()

        if not transaction:
            raise ValueError("Transaction not found")

        # Verify ownership through bank account
        if (
            transaction.bank_account.user_id != user_id
            or not transaction.bank_account.is_active
        ):
            raise ValueError("Access denied")

        # Track if category changed for learning
        old_category_id = transaction.category_id
        category_changed = False
        verified_changed = (
            'verified' in data
            and data['verified'] != transaction.verified
        )

        # Update allowed fields
        if 'category_id' in data:
            category_id = data['category_id']
            if category_id is not None:
                # Verify category exists
                category = TransactionCategory.query.filter_by(
                    id=category_id,
                    is_system=True,
                ).first()
                if not category:
                    raise ValueError("Invalid category_id")

            # Check if category actually changed
            if category_id != old_category_id:
                category_changed = True
                transaction.category_id = category_id

        if 'notes' in data:
            transaction.notes = data['notes']

        if 'verified' in data:
            transaction.verified = data['verified']

        # Update timestamp
        transaction.updated_at = datetime.utcnow()

        if verified_changed:
            db.session.flush()
            from app.services.bank_statement_service import (
                BankStatementService,
            )
            BankStatementService._recalculate_account_statement_state(
                transaction.bank_account_id
            )

        db.session.commit()

        # Learn from user's category correction
        if category_changed and transaction.category_id is not None:
            try:
                from app.services.transaction_categorization_service import TransactionCategorizationService
                TransactionCategorizationService.learn_from_user_correction(
                    transaction_id, transaction.category_id
                )
            except Exception:
                # Don't fail the update if learning fails
                logger.warning("Failed to propagate category correction")

        # Return updated transaction with category info
        txn_dict = transaction.to_dict()
        if transaction.category and transaction.category.is_system:
            txn_dict['category'] = transaction.category.to_dict()
        else:
            txn_dict['category_id'] = None
            txn_dict['category'] = None

        return txn_dict

    @staticmethod
    def delete_transaction(transaction_id, user_id):
        """
        Delete a transaction (hard delete).

        Args:
            transaction_id: ID of the transaction
            user_id: ID of the user making the request

        Raises:
            ValueError: If transaction not found or access denied
        """
        # Check if transaction exists
        transaction = Transaction.query.filter_by(id=transaction_id).first()

        if not transaction:
            raise ValueError("Transaction not found")

        # Verify ownership through bank account
        if (
            transaction.bank_account.user_id != user_id
            or not transaction.bank_account.is_active
        ):
            raise ValueError("Access denied")

        bank_account_id = transaction.bank_account_id
        db.session.delete(transaction)
        db.session.flush()

        # current_balance is a cache derived from the newest verified running
        # balance. Keep it coherent when a user deletes that source row.
        from app.services.bank_statement_service import BankStatementService
        BankStatementService._recalculate_account_statement_state(
            bank_account_id
        )
        db.session.commit()

    @staticmethod
    def bulk_recategorize(transaction_ids, category_id, user_id):
        """
        Bulk recategorize multiple transactions.

        Args:
            transaction_ids: List of transaction IDs
            category_id: Category ID to apply to all transactions
            user_id: ID of the user making the request

        Returns:
            dict: Result with updated count and IDs

        Raises:
            ValueError: If invalid data or access denied
        """
        if (
            not isinstance(transaction_ids, list)
            or not 1 <= len(transaction_ids) <= 500
            or any(
                isinstance(transaction_id, bool)
                or not isinstance(transaction_id, int)
                or transaction_id <= 0
                for transaction_id in transaction_ids
            )
            or len(set(transaction_ids)) != len(transaction_ids)
        ):
            raise ValueError(
                'transaction_ids must contain 1-500 unique positive integers'
            )
        if (
            isinstance(category_id, bool)
            or not isinstance(category_id, int)
            or category_id <= 0
        ):
            raise ValueError('category_id must be a positive integer')

        # Verify category exists
        category = TransactionCategory.query.filter_by(
            id=category_id,
            is_system=True,
        ).first()
        if not category:
            raise ValueError("Invalid category_id")

        # Get all transactions and verify ownership
        transactions = Transaction.query.filter(
            Transaction.id.in_(transaction_ids)
        ).all()

        if not transactions:
            raise ValueError("No transactions found with provided IDs")
        if len(transactions) != len(transaction_ids):
            raise ValueError(
                'One or more transactions were not found or are unavailable'
            )

        # Check ownership for all transactions
        for txn in transactions:
            if (
                txn.bank_account.user_id != user_id
                or not txn.bank_account.is_active
            ):
                raise ValueError(f"Access denied for transaction {txn.id}")

        # Update all transactions
        updated_ids = []
        for txn in transactions:
            old_category_id = txn.category_id
            if old_category_id != category_id:
                txn.category_id = category_id
                txn.category_confidence = 0.6  # Lower confidence for bulk update
                txn.updated_at = datetime.utcnow()
                updated_ids.append(txn.id)

        db.session.commit()

        logger.info(f"Bulk recategorized {len(updated_ids)} transactions to category {category_id}")

        return {
            'updated_count': len(updated_ids),
            'updated_ids': updated_ids
        }
