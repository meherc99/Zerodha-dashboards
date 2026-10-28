"""
AI-backed transaction categorization via an OpenAI-compatible chat API.

The model is asked to pick exactly one category name from the known system
categories. Any transport, timeout, or parsing failure returns ``None`` so the
caller can fall back to keyword rules / Uncategorized without breaking the
statement workflow.
"""
import logging
import re
from decimal import Decimal
from typing import List, Optional

import requests
from flask import current_app

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = 'http://localhost:20128/v1'
DEFAULT_MODEL = 'openrouter/openrouter/free'
DEFAULT_TIMEOUT = 30
# Reasoning models emit thinking tokens before the answer; keep this high
# enough for the final category name to be produced.
DEFAULT_MAX_TOKENS = 2048
MAX_DESCRIPTION_CHARS = 300
# Transactions per AI request. The endpoint allows 40 requests/minute, so
# batching keeps a large statement well under that ceiling.
BATCH_SIZE = 30


class AICategorizationService:
    """Categorize transactions using an OpenAI-compatible LLM endpoint."""

    @staticmethod
    def _config():
        """Read AI settings from Flask config, falling back to defaults."""
        try:
            cfg = current_app.config
        except RuntimeError:
            return {
                'enabled': False,
                'base_url': DEFAULT_BASE_URL,
                'model': DEFAULT_MODEL,
                'api_key': None,
                'timeout': DEFAULT_TIMEOUT,
                'max_tokens': DEFAULT_MAX_TOKENS,
            }
        return {
            'enabled': bool(cfg.get('AI_CATEGORIZATION_ENABLED', False)),
            'base_url': cfg.get('AI_CATEGORIZATION_BASE_URL', DEFAULT_BASE_URL),
            'model': cfg.get('AI_CATEGORIZATION_MODEL', DEFAULT_MODEL),
            'api_key': cfg.get('AI_CATEGORIZATION_API_KEY'),
            'timeout': cfg.get('AI_CATEGORIZATION_TIMEOUT', DEFAULT_TIMEOUT),
            'max_tokens': cfg.get(
                'AI_CATEGORIZATION_MAX_TOKENS', DEFAULT_MAX_TOKENS
            ),
        }

    @staticmethod
    def is_enabled() -> bool:
        """Return whether AI categorization is configured and enabled."""
        config = AICategorizationService._config()
        return bool(config['enabled'] and config['base_url'])

    @staticmethod
    def _build_messages(description: str, amount: Decimal, categories: List[str]):
        category_list = ', '.join(categories)
        system_prompt = (
            'You are a bank transaction categorizer. Given a transaction '
            'description, choose the single best category from this exact '
            f'list: {category_list}. Reply with only the category name, '
            "exactly as written, and nothing else. If none clearly fit, "
            "reply 'Uncategorized'."
        )
        amount_hint = ''
        try:
            if amount is not None:
                amount_hint = f' Amount: {Decimal(amount)}.'
        except (TypeError, ValueError):
            amount_hint = ''
        user_prompt = (
            f'Transaction: "{description[:MAX_DESCRIPTION_CHARS]}".'
            f'{amount_hint} Category:'
        )
        return [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

    @staticmethod
    def predict_category(
        description: str,
        categories: List[str],
        amount: Optional[Decimal] = None,
    ) -> Optional[str]:
        """Return the model's chosen category name, or ``None`` on failure.

        The returned value is guaranteed to be one of ``categories`` (matched
        case-insensitively); anything else yields ``None``.
        """
        if not description or not categories:
            return None

        config = AICategorizationService._config()
        if not config['enabled'] or not config['base_url']:
            return None

        url = f"{str(config['base_url']).rstrip('/')}/chat/completions"
        headers = {'Content-Type': 'application/json'}
        if config['api_key']:
            headers['Authorization'] = f"Bearer {config['api_key']}"
        payload = {
            'model': config['model'],
            'messages': AICategorizationService._build_messages(
                description, amount, categories
            ),
            'temperature': 0,
            'max_tokens': config['max_tokens'],
            'stream': False,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=config['timeout'],
            )
            response.raise_for_status()
            data = response.json()
            content = (
                data['choices'][0]['message']['content'] or ''
            ).strip()
        except (requests.RequestException, ValueError, KeyError, IndexError):
            logger.warning("AI categorization request failed; falling back")
            return None

        return AICategorizationService._match_category(content, categories)

    @staticmethod
    def predict_categories_batch(
        items: List[tuple],
        categories: List[str],
    ) -> List[Optional[str]]:
        """Predict categories for many transactions using batched requests.

        Transactions are grouped into batches of ``BATCH_SIZE`` so a large
        statement stays within the endpoint's request-rate limit. Each result
        is one of ``categories`` (matched case-insensitively) or ``None``.

        Args:
            items: list of ``(description, amount)`` tuples.
            categories: allowed category names.

        Returns:
            List aligned with ``items``.
        """
        results: List[Optional[str]] = [None] * len(items)
        if not items or not categories:
            return results

        config = AICategorizationService._config()
        if not config['enabled'] or not config['base_url']:
            return results

        for start in range(0, len(items), BATCH_SIZE):
            chunk = items[start:start + BATCH_SIZE]
            answers = AICategorizationService._predict_chunk(
                chunk, categories, config
            )
            for offset, answer in enumerate(answers):
                results[start + offset] = answer
        return results

    @staticmethod
    def _build_batch_messages(items: List[tuple], categories: List[str]):
        category_list = ', '.join(categories)
        system_prompt = (
            'You are a bank transaction categorizer. For each numbered '
            'transaction, choose the single best category from this exact '
            f'list: {category_list}. Reply with one line per transaction in '
            "the format '<number>. <Category>', using the category name "
            "exactly as written. If none clearly fit, use 'Uncategorized'. "
            'Output only these lines and nothing else.'
        )
        lines = []
        for index, (description, amount) in enumerate(items, start=1):
            text = str(description or '')[:MAX_DESCRIPTION_CHARS]
            amount_hint = ''
            try:
                if amount is not None:
                    amount_hint = f' (Amount: {Decimal(amount)})'
            except (TypeError, ValueError):
                amount_hint = ''
            lines.append(f'{index}. "{text}"{amount_hint}')
        user_prompt = 'Transactions:\n' + '\n'.join(lines) + '\nCategories:'
        return [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ]

    @staticmethod
    def _predict_chunk(
        items: List[tuple],
        categories: List[str],
        config: dict,
    ) -> List[Optional[str]]:
        """Send one batch request and align answers back to ``items``."""
        answers: List[Optional[str]] = [None] * len(items)

        url = f"{str(config['base_url']).rstrip('/')}/chat/completions"
        headers = {'Content-Type': 'application/json'}
        if config['api_key']:
            headers['Authorization'] = f"Bearer {config['api_key']}"
        # Reserve room for one answer line per transaction on top of the
        # configured budget so batched replies are not truncated.
        max_tokens = max(config['max_tokens'], 64 * len(items) + 256)
        payload = {
            'model': config['model'],
            'messages': AICategorizationService._build_batch_messages(
                items, categories
            ),
            'temperature': 0,
            'max_tokens': max_tokens,
            'stream': False,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=config['timeout'],
            )
            response.raise_for_status()
            data = response.json()
            content = (
                data['choices'][0]['message']['content'] or ''
            ).strip()
        except (requests.RequestException, ValueError, KeyError, IndexError):
            logger.warning("AI batch categorization request failed; falling back")
            return answers

        parsed = AICategorizationService._parse_batch_content(content)
        for index in range(len(items)):
            raw = parsed.get(index + 1)
            if raw:
                answers[index] = AICategorizationService._match_category(
                    raw, categories
                )
        return answers

    @staticmethod
    def _parse_batch_content(content: str) -> dict:
        """Parse '<number>. <Category>' lines into a ``{number: text}`` map."""
        parsed = {}
        for line in content.splitlines():
            match = re.match(r'\s*(\d+)[\.\):]\s*(.+?)\s*$', line)
            if match:
                parsed[int(match.group(1))] = match.group(2)
        return parsed

    @staticmethod
    def _match_category(content: str, categories: List[str]) -> Optional[str]:
        """Map free-form model output to one of the allowed category names."""
        if not content:
            return None
        cleaned = content.strip().strip('."\'` ').lower()
        if not cleaned:
            return None

        lookup = {name.lower(): name for name in categories}
        if cleaned in lookup:
            return lookup[cleaned]

        # Tolerate extra words by preferring the longest contained category.
        matches = [
            name for name in categories if name.lower() in cleaned
        ]
        if matches:
            return max(matches, key=len)
        return None
