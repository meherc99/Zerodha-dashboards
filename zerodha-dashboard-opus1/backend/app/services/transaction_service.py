"""
Transaction service for managing and querying bank transactions.
"""
from datetime import datetime
from sqlalchemy import or_, and_
from app.database import db
from app.models.transaction import Transaction
from app.models.transaction_category import TransactionCategory
from app.models.bank_account import BankAccount


class TransactionService:
    """Service for transaction management and queries"""

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
        bank_account = BankAccount.query.filter_by(id=bank_account_id).first()

        if not bank_account:
            raise ValueError("Bank account not found")

        # Verify ownership
        if bank_account.user_id != user_id:
            raise ValueError("Access denied")

        # Build base query
        query = Transaction.query.filter_by(bank_account_id=bank_account_id)

        # Apply date filters
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(Transaction.transaction_date >= date_from)
            except ValueError:
                raise ValueError("Invalid date_from format. Use YYYY-MM-DD")

        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(Transaction.transaction_date <= date_to)
            except ValueError:
                raise ValueError("Invalid date_to format. Use YYYY-MM-DD")

        # Apply type filter
        if filters.get('type') and filters['type'] != 'all':
            if filters['type'] not in ['credit', 'debit']:
                raise ValueError("Type must be 'credit', 'debit', or 'all'")
            query = query.filter(Transaction.transaction_type == filters['type'])

        # Apply category filter
        if filters.get('category_id'):
            query = query.filter(Transaction.category_id == int(filters['category_id']))

        # Apply search filter
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(Transaction.description.ilike(search_term))

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_by = filters.get('sort_by', 'date')
        order = filters.get('order', 'desc')

        if sort_by == 'date':
            sort_column = Transaction.transaction_date
        elif sort_by == 'amount':
            sort_column = Transaction.amount
        elif sort_by == 'description':
            sort_column = Transaction.description
        else:
            sort_column = Transaction.transaction_date

        if order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        page = max(int(filters.get('page', 1)), 1)
        limit = min(int(filters.get('limit', 50)), 200)  # Cap at 200
        offset = (page - 1) * limit

        transactions = query.offset(offset).limit(limit).all()

        # Calculate total pages
        pages = (total + limit - 1) // limit if total > 0 else 0

        # Convert to dicts with category info
        transaction_dicts = []
        for txn in transactions:
            txn_dict = txn.to_dict()

            # Add category info
            if txn.category:
                txn_dict['category'] = txn.category.to_dict()
            else:
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
            BankAccount.user_id == user_id
        )

        # Apply date filters
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(Transaction.transaction_date >= date_from)
            except ValueError:
                raise ValueError("Invalid date_from format. Use YYYY-MM-DD")

        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(Transaction.transaction_date <= date_to)
            except ValueError:
                raise ValueError("Invalid date_to format. Use YYYY-MM-DD")

        # Apply type filter
        if filters.get('type') and filters['type'] != 'all':
            if filters['type'] not in ['credit', 'debit']:
                raise ValueError("Type must be 'credit', 'debit', or 'all'")
            query = query.filter(Transaction.transaction_type == filters['type'])

        # Apply category filter
        if filters.get('category_id'):
            query = query.filter(Transaction.category_id == int(filters['category_id']))

        # Apply search filter
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            query = query.filter(Transaction.description.ilike(search_term))

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        sort_by = filters.get('sort_by', 'date')
        order = filters.get('order', 'desc')

        if sort_by == 'date':
            sort_column = Transaction.transaction_date
        elif sort_by == 'amount':
            sort_column = Transaction.amount
        elif sort_by == 'description':
            sort_column = Transaction.description
        else:
            sort_column = Transaction.transaction_date

        if order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Apply pagination
        page = max(int(filters.get('page', 1)), 1)
        limit = min(int(filters.get('limit', 50)), 200)
        offset = (page - 1) * limit

        transactions = query.offset(offset).limit(limit).all()

        # Calculate total pages
        pages = (total + limit - 1) // limit if total > 0 else 0

        # Convert to dicts with category and bank account info
        transaction_dicts = []
        for txn in transactions:
            txn_dict = txn.to_dict()

            # Add category info
            if txn.category:
                txn_dict['category'] = txn.category.to_dict()
            else:
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
        # Check if transaction exists
        transaction = Transaction.query.filter_by(id=transaction_id).first()

        if not transaction:
            raise ValueError("Transaction not found")

        # Verify ownership through bank account
        if transaction.bank_account.user_id != user_id:
            raise ValueError("Access denied")

        # Check for disallowed fields
        disallowed_fields = ['amount', 'transaction_date', 'description', 'transaction_type', 'running_balance']
        for field in disallowed_fields:
            if field in data:
                raise ValueError(f"Cannot update field: {field}")

        # Track if category changed for learning
        old_category_id = transaction.category_id
        category_changed = False

        # Update allowed fields
        if 'category_id' in data:
            category_id = data['category_id']
            if category_id is not None:
                # Verify category exists
                category = TransactionCategory.query.get(category_id)
                if not category:
                    raise ValueError("Invalid category_id")

            # Check if category actually changed
            if category_id != old_category_id:
                category_changed = True
                transaction.category_id = category_id

        if 'notes' in data:
            transaction.notes = data['notes']

        if 'verified' in data:
            transaction.verified = bool(data['verified'])

        # Update timestamp
        transaction.updated_at = datetime.utcnow()

        db.session.commit()

        # Learn from user's category correction
        if category_changed and transaction.category_id is not None:
            try:
                from app.services.transaction_categorization_service import TransactionCategorizationService
                TransactionCategorizationService.learn_from_user_correction(
                    transaction_id, transaction.category_id
                )
            except Exception as learn_error:
                # Don't fail the update if learning fails
                logger.warning(f"Failed to learn from category correction: {learn_error}")

        # Return updated transaction with category info
        txn_dict = transaction.to_dict()
        if transaction.category:
            txn_dict['category'] = transaction.category.to_dict()
        else:
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
        if transaction.bank_account.user_id != user_id:
            raise ValueError("Access denied")

        db.session.delete(transaction)
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
        # Verify category exists
        category = TransactionCategory.query.get(category_id)
        if not category:
            raise ValueError("Invalid category_id")

        # Get all transactions and verify ownership
        transactions = Transaction.query.filter(
            Transaction.id.in_(transaction_ids)
        ).all()

        if not transactions:
            raise ValueError("No transactions found with provided IDs")

        # Check ownership for all transactions
        for txn in transactions:
            if txn.bank_account.user_id != user_id:
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
