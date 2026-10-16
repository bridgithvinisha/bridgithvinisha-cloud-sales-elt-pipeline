import pandas as pd
import pytest

from src.validate import validate_and_clean


def sample_rows():
    return pd.DataFrame(
        [
            {"order_id": "O1", "order_line_id": "1", "order_date": "2025-01-01", "customer_id": "C1", "product_id": "P1", "quantity": "2", "unit_price": "10", "discount": "0.1"},
        ]
    )


def test_calculates_sales_amount_and_defaults_optional_fields():
    clean, rejected, metrics = validate_and_clean(sample_rows())
    assert rejected.empty
    assert clean.iloc[0]["sales_amount"] == 18.0
    assert clean.iloc[0]["category"] == "Unknown"
    assert metrics["accepted_rows"] == 1


@pytest.mark.parametrize(
    ("column", "value", "expected_reason"),
    [
        ("order_date", "not-a-date", "invalid_order_date"),
        ("quantity", "0", "non_positive_quantity"),
        ("quantity", "-2", "non_positive_quantity"),
        ("quantity", "2.5", "non_integer_quantity"),
        ("quantity", "many", "invalid_quantity"),
        ("unit_price", "-0.01", "negative_unit_price"),
        ("unit_price", "free", "invalid_unit_price"),
        ("discount", "invalid", "invalid_discount"),
        ("customer_id", None, "missing_customer_id"),
    ],
)
def test_invalid_rows_are_quarantined(column, value, expected_reason):
    rows = sample_rows()
    rows.loc[0, column] = value
    clean, rejected, metrics = validate_and_clean(rows)
    assert clean.empty
    assert expected_reason in rejected.iloc[0]["rejection_reason"]
    assert metrics["rejected_rows"] == 1


def test_missing_required_column_fails_fast():
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_and_clean(pd.DataFrame({"order_id": ["O1"]}))


def test_exact_duplicates_keep_one_record():
    rows = pd.concat([sample_rows(), sample_rows()], ignore_index=True)
    clean, rejected, metrics = validate_and_clean(rows)
    assert len(clean) == 1
    assert rejected.empty
    assert metrics["exact_duplicates_dropped"] == 1


def test_conflicting_duplicate_order_line_is_quarantined():
    rows = sample_rows()
    second = sample_rows()
    second.loc[0, "quantity"] = "3"
    clean, rejected, _ = validate_and_clean(pd.concat([rows, second], ignore_index=True))
    assert clean.empty
    assert len(rejected) == 2
    assert set(rejected["rejection_reason"]) == {"conflicting_duplicate_business_key"}