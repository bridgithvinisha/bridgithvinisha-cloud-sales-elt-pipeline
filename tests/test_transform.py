import pandas as pd

from src.transform import select_output_columns
from src.validate import validate_and_clean


def test_transform_has_stable_schema():
    rows = pd.DataFrame(
        [{"order_id": "O1", "order_line_id": "1", "order_date": "2025-01-01", "customer_id": "C1", "product_id": "P1", "quantity": 2, "unit_price": 4.5}]
    )
    clean, _, _ = validate_and_clean(rows)
    transformed = select_output_columns(clean)
    assert transformed.columns.tolist() == [
        "order_id", "order_line_id", "order_date", "customer_id", "customer_name",
        "product_id", "product_name", "category", "quantity", "unit_price",
        "discount", "country", "sales_amount",
    ]