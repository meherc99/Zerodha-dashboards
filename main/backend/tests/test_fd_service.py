"""Financial boundary tests for fixed-deposit valuation."""
from datetime import date

import pytest

from app.services.fd_service import FDService


@pytest.mark.parametrize(
    (
        "valuation_date",
        "expected_days",
        "expected_interest",
        "expected_value",
        "is_matured",
    ),
    [
        (date(2025, 7, 1), 181, 3620.00, 103620.00, False),
        (date(2026, 1, 1), 365, 7300.00, 107300.00, True),
        (date(2027, 6, 1), 365, 7300.00, 107300.00, True),
    ],
)
def test_fd_accrual_is_capped_at_maturity(
    valuation_date,
    expected_days,
    expected_interest,
    expected_value,
    is_matured,
):
    result = FDService.calculate_fd_returns(
        investment_amount="100000",
        investment_date=date(2025, 1, 1),
        interest_rate="7.3",
        maturity_date=date(2026, 1, 1),
        valuation_date=valuation_date,
    )

    assert result["days_elapsed"] == expected_days
    assert result["interest_earned"] == expected_interest
    assert result["current_value"] == expected_value
    assert result["is_matured"] is is_matured
    assert result["valuation_date"] == min(
        valuation_date,
        date(2026, 1, 1),
    ).isoformat()


def test_fd_without_maturity_accrues_only_to_explicit_valuation_date():
    result = FDService.calculate_fd_returns(
        investment_amount="36500",
        investment_date=date(2025, 1, 1),
        interest_rate="10",
        valuation_date=date(2025, 1, 31),
    )

    assert result == {
        "days_elapsed": 30,
        "years_elapsed": pytest.approx(30 / 365, abs=0.0001),
        "interest_earned": 300.0,
        "current_value": 36800.0,
        "valuation_date": "2025-01-31",
        "is_matured": False,
    }


def test_future_dated_investment_never_accrues_negative_interest():
    result = FDService.calculate_fd_returns(
        investment_amount=250000,
        investment_date=date(2026, 4, 1),
        interest_rate=8,
        maturity_date=date(2027, 4, 1),
        valuation_date=date(2026, 1, 1),
    )

    assert result["days_elapsed"] == 0
    assert result["years_elapsed"] == 0
    assert result["interest_earned"] == 0
    assert result["current_value"] == 250000
    assert result["is_matured"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("investment_amount", "not-money"),
        ("interest_rate", "not-a-rate"),
        ("investment_date", "not-a-date"),
        ("maturity_date", "not-a-date"),
        ("valuation_date", "not-a-date"),
    ],
)
def test_fd_rejects_unparseable_financial_inputs(field, value):
    arguments = {
        "investment_amount": 100000,
        "investment_date": date(2025, 1, 1),
        "interest_rate": 7,
        "maturity_date": date(2026, 1, 1),
        "valuation_date": date(2025, 6, 1),
    }
    arguments[field] = value

    with pytest.raises((ValueError, TypeError)):
        FDService.calculate_fd_returns(**arguments)


def test_fd_holding_keys_distinguish_deposits_at_the_same_bank():
    first = {
        "bank_name": "Example Bank",
        "investment_date": date(2025, 1, 1),
        "maturity_date": date(2026, 1, 1),
        "source_row": 2,
    }
    second = {**first, "source_row": 3}

    assert FDService._holding_key(first) != FDService._holding_key(second)
    assert FDService._holding_key({**first, "deposit_id": "FD-123"}) == "fd:FD-123"


def test_fd_rejects_derived_value_that_exceeds_database_precision():
    with pytest.raises(
        ValueError,
        match='Fixed-deposit value exceeds database precision',
    ):
        FDService.calculate_fd_returns(
            investment_amount='9999999999999.99',
            investment_date=date(2025, 1, 1),
            interest_rate='1',
            valuation_date=date(2026, 1, 1),
        )
