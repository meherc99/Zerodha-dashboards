"""Tests for the AI-backed transaction categorization pipeline."""

from decimal import Decimal
from unittest.mock import patch

from app.database import db
from app.models.transaction_category import TransactionCategory
from app.services.ai_categorization_service import AICategorizationService
from app.services.transaction_categorization_service import (
    TransactionCategorizationService,
)


def _seed_categories():
    categories = [
        TransactionCategory(
            name='Groceries', icon='🛒', color='#10b981',
            keywords=['grocery'], is_system=True
        ),
        TransactionCategory(
            name='Entertainment', icon='🎬', color='#a855f7',
            keywords=['netflix'], is_system=True
        ),
        TransactionCategory(
            name='Uncategorized', icon='❓', color='#9ca3af',
            keywords=[], is_system=True
        ),
    ]
    db.session.add_all(categories)
    db.session.commit()


def _completion(content):
    class _Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {'choices': [{'message': {'content': content}}]}

    return _Response()


def test_ai_disabled_by_default_returns_none(app):
    with app.app_context():
        assert AICategorizationService.is_enabled() is False
        result = AICategorizationService.predict_category(
            'Spotify subscription', ['Entertainment'], Decimal('9.99')
        )
        assert result is None


def test_predict_category_matches_allowed_name(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        with patch('app.services.ai_categorization_service.requests.post',
                   return_value=_completion('Entertainment')) as mocked:
            result = AICategorizationService.predict_category(
                'ACME STREAMING SERVICE',
                ['Groceries', 'Entertainment', 'Uncategorized'],
                Decimal('12.00'),
            )
        assert result == 'Entertainment'
        called_url = mocked.call_args.args[0]
        assert called_url.endswith('/v1/chat/completions')
        payload = mocked.call_args.kwargs['json']
        assert payload['model'] == app.config['AI_CATEGORIZATION_MODEL']


def test_predict_category_rejects_unknown_answer(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        with patch('app.services.ai_categorization_service.requests.post',
                   return_value=_completion('Cryptocurrency')):
            result = AICategorizationService.predict_category(
                'Some purchase', ['Groceries', 'Entertainment']
            )
        assert result is None


def test_predict_category_returns_none_on_request_error(app):
    import requests

    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        with patch('app.services.ai_categorization_service.requests.post',
                   side_effect=requests.ConnectionError('down')):
            result = AICategorizationService.predict_category(
                'Some purchase', ['Groceries', 'Entertainment']
            )
        assert result is None


def test_auto_categorize_uses_ai_when_keywords_miss(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        _seed_categories()
        with patch('app.services.ai_categorization_service.requests.post',
                   return_value=_completion('Entertainment')):
            category_id, confidence = (
                TransactionCategorizationService.auto_categorize(
                    'ACME STREAMING SERVICE', Decimal('12.00')
                )
            )
        entertainment = TransactionCategory.query.filter_by(
            name='Entertainment'
        ).first()
        assert category_id == entertainment.id
        assert confidence == 0.85


def test_auto_categorize_falls_back_to_uncategorized_when_ai_uncertain(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        _seed_categories()
        with patch('app.services.ai_categorization_service.requests.post',
                   return_value=_completion('Uncategorized')):
            category_id, confidence = (
                TransactionCategorizationService.auto_categorize(
                    'Totally unknown vendor', Decimal('5.00')
                )
            )
        uncategorized = TransactionCategory.query.filter_by(
            name='Uncategorized'
        ).first()
        assert category_id == uncategorized.id
        assert confidence == 0.5


def test_keyword_match_takes_precedence_over_ai(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        _seed_categories()
        with patch('app.services.ai_categorization_service.requests.post') as post:
            category_id, confidence = (
                TransactionCategorizationService.auto_categorize(
                    'Weekly grocery run', Decimal('30.00')
                )
            )
        groceries = TransactionCategory.query.filter_by(name='Groceries').first()
        assert category_id == groceries.id
        assert confidence == 0.8
        post.assert_not_called()


def _batch_completion(lines):
    class _Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {'choices': [{'message': {'content': '\n'.join(lines)}}]}

    return _Response()


def test_predict_categories_batch_aligns_answers(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        items = [
            ('NETFLIX monthly', Decimal('15.99')),
            ('UBER trip', Decimal('12.50')),
            ('WEIRD VENDOR', Decimal('3.00')),
        ]
        content = ['1. Entertainment', '2. Transportation', '3. Nonsense']
        with patch('app.services.ai_categorization_service.requests.post',
                   return_value=_batch_completion(content)) as post:
            result = AICategorizationService.predict_categories_batch(
                items,
                ['Entertainment', 'Transportation', 'Groceries', 'Uncategorized'],
            )
        assert result == ['Entertainment', 'Transportation', None]
        # A single batch request for all three transactions.
        assert post.call_count == 1


def test_predict_categories_batch_groups_into_batches_of_30(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        items = [(f'vendor {i}', Decimal('1.00')) for i in range(65)]

        def _respond(*args, **kwargs):
            count = len(kwargs['json']['messages'][1]['content'].splitlines()) - 2
            lines = [f'{i + 1}. Groceries' for i in range(count)]
            return _batch_completion(lines)

        with patch('app.services.ai_categorization_service.requests.post',
                   side_effect=_respond) as post:
            result = AICategorizationService.predict_categories_batch(
                items, ['Groceries', 'Uncategorized']
            )
        assert len(result) == 65
        assert all(name == 'Groceries' for name in result)
        # 65 transactions -> ceil(65/30) == 3 requests.
        assert post.call_count == 3


def test_categorize_batch_keyword_first_then_batched_ai(app):
    app.config['AI_CATEGORIZATION_ENABLED'] = True
    with app.app_context():
        _seed_categories()
        items = [
            ('Weekly grocery run', Decimal('30.00')),   # keyword -> Groceries
            ('ACME STREAMING', Decimal('12.00')),       # AI -> Entertainment
            ('', Decimal('0.00')),                       # empty -> Uncategorized
        ]
        with patch('app.services.ai_categorization_service.requests.post',
                   return_value=_batch_completion(['1. Entertainment'])) as post:
            results = TransactionCategorizationService.categorize_batch(items)

        groceries = TransactionCategory.query.filter_by(name='Groceries').first()
        entertainment = TransactionCategory.query.filter_by(
            name='Entertainment'
        ).first()
        uncategorized = TransactionCategory.query.filter_by(
            name='Uncategorized'
        ).first()
        assert results[0] == (groceries.id, 0.8)
        assert results[1] == (entertainment.id, 0.85)
        assert results[2] == (uncategorized.id, 0.5)
        # Only the single keyword-miss reached the AI, in one batch request.
        assert post.call_count == 1
        sent = post.call_args.kwargs['json']['messages'][1]['content']
        assert 'ACME STREAMING' in sent
        assert 'Weekly grocery run' not in sent

