import pandas as pd
import pytest

from src.extract import profile_dataframe, read_sales_csv


def test_read_csv_and_profile(tmp_path):
    source = tmp_path / "input.csv"
    pd.DataFrame({"order_id": ["O1"], "quantity": ["2"]}).to_csv(source, index=False)
    result = read_sales_csv(source)
    assert result.loc[0, "quantity"] == "2"
    assert profile_dataframe(result)["row_count"] == 1


def test_missing_file_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="does not exist"):
        read_sales_csv(tmp_path / "missing.csv")