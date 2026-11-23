import pandas as pd
import pytest

from src.metrics import financial_data_available, hit_rate, is_hit, profit, roi


def test_missing_or_non_positive_financials_are_excluded() -> None:
    films = pd.DataFrame(
        {
            "budget": [100, None, 100, 0, 100],
            "revenue": [200, 200, 0, 200, 50],
            "vote_count": [2000, 2000, 2000, 2000, 2000],
            "vote_average": [8.0, 8.0, 8.0, 8.0, 8.0],
        }
    )

    assert financial_data_available(films).tolist() == [
        True,
        False,
        False,
        False,
        True,
    ]
    assert is_hit(films).tolist() == [True, False, False, False, False]
    assert hit_rate(films) == pytest.approx(0.5)
    assert roi(films).iloc[0] == pytest.approx(2.0)
    assert profit(films).iloc[0] == pytest.approx(100)
    assert roi(films).iloc[1:].isna().tolist() == [True, True, True, False]
    assert profit(films).iloc[1:].isna().tolist() == [True, True, True, False]


def test_hit_rate_is_zero_when_no_financial_records_are_eligible() -> None:
    films = pd.DataFrame(
        {
            "budget": [0, None],
            "revenue": [100, 100],
            "vote_count": [2000, 2000],
            "vote_average": [8.0, 8.0],
        }
    )

    assert hit_rate(films) == 0.0
