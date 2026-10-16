"""Read and profile source CSV files without modifying them."""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def read_sales_csv(path: str | Path) -> pd.DataFrame:
    """Load a CSV as strings first so validation controls type conversion."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Input CSV does not exist: {source}")
    try:
        frame = pd.read_csv(source, dtype="string", keep_default_na=True)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        logger.exception("Unable to read source CSV %s", source.name)
        raise ValueError(f"Could not read CSV {source.name}: {exc}") from exc
    logger.info("Extracted %d rows from %s", len(frame), source.name)
    return frame


def profile_dataframe(frame: pd.DataFrame) -> dict:
    """Return basic shape, null counts, and distinct counts for inspection."""
    return {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": list(frame.columns),
        "null_counts": {str(k): int(v) for k, v in frame.isna().sum().items()},
        "distinct_counts": {str(k): int(v) for k, v in frame.nunique(dropna=True).items()},
    }