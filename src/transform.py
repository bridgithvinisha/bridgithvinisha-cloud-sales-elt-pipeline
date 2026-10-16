"""Local transformation helpers for the sales pipeline."""

import pandas as pd

from .config import OUTPUT_COLUMNS


def select_output_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return cleaned data in the stable public output schema."""
    return frame.loc[:, OUTPUT_COLUMNS].copy()