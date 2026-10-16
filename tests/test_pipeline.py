import json

import pandas as pd

from src.run_pipeline import run_pipeline


def test_pipeline_writes_outputs_and_is_repeatable(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "processed"
    pd.DataFrame(
        [{"order_id": "O1", "order_line_id": "1", "order_date": "2025-01-01", "customer_id": "C1", "product_id": "P1", "quantity": 2, "unit_price": 4.5}]
    ).to_csv(source, index=False)
    before = source.read_bytes()

    first = run_pipeline(source, output)
    first_csv = (output / "cleaned_sales.csv").read_bytes()
    second = run_pipeline(source, output)

    assert source.read_bytes() == before
    assert first["validation"] == second["validation"]
    assert (output / "cleaned_sales.csv").read_bytes() == first_csv
    assert json.loads((output / "quality_summary.json").read_text())["validation"]["accepted_rows"] == 1
    assert pd.read_csv(output / "cleaned_sales.csv").loc[0, "sales_amount"] == 9.0