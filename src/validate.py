"""Validate source records and separate accepted rows from quarantine rows."""

import logging

import pandas as pd

from .config import OPTIONAL_COLUMNS, REQUIRED_COLUMNS

logger = logging.getLogger(__name__)
BUSINESS_KEY = ["order_id", "order_line_id"]
REQUIRED_VALUES = ["order_id", "order_line_id", "order_date", "customer_id", "product_id"]


def validate_and_clean(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Apply documented rules; return clean, rejected, and validation metrics.

    Exact duplicate source rows keep their first occurrence. If a business key
    (order_id, order_line_id) has conflicting content, every row for that key
    is quarantined rather than choosing an arbitrary winner.
    """
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    work = frame.copy()
    for column in OPTIONAL_COLUMNS:
        if column not in work.columns:
            work[column] = pd.NA

    for column in REQUIRED_VALUES + ["customer_name", "product_name", "category", "country"]:
        work[column] = work[column].astype("string").str.strip()
    work["order_date"] = pd.to_datetime(work["order_date"], errors="coerce", utc=True).dt.date
    work["quantity"] = pd.to_numeric(work["quantity"], errors="coerce")
    work["unit_price"] = pd.to_numeric(work["unit_price"], errors="coerce")
    discount_raw = work["discount"].astype("string").str.strip()
    parsed_discount = pd.to_numeric(discount_raw, errors="coerce")
    invalid_discount = discount_raw.notna() & discount_raw.ne("") & parsed_discount.isna()
    work["discount"] = parsed_discount.fillna(0.0)

    reasons: list[list[str]] = [[] for _ in range(len(work))]
    for position, (_, row) in enumerate(work.iterrows()):
        for column in REQUIRED_VALUES:
            if pd.isna(row[column]) or row[column] == "":
                reasons[position].append(f"missing_{column}")
        if pd.isna(row["order_date"]):
            reasons[position].append("invalid_order_date")
        if pd.isna(row["quantity"]):
            reasons[position].append("invalid_quantity")
        elif row["quantity"] <= 0:
            reasons[position].append("non_positive_quantity")
        elif row["quantity"] % 1 != 0:
            reasons[position].append("non_integer_quantity")
        if pd.isna(row["unit_price"]):
            reasons[position].append("invalid_unit_price")
        elif row["unit_price"] < 0:
            reasons[position].append("negative_unit_price")
        if not 0 <= row["discount"] <= 1:
            reasons[position].append("discount_out_of_range")
        if bool(invalid_discount.iloc[position]):
            reasons[position].append("invalid_discount")

    invalid_mask = pd.Series([bool(items) for items in reasons], index=work.index)
    valid = work.loc[~invalid_mask].copy()
    rejected = work.loc[invalid_mask].copy()
    rejected["rejection_reason"] = [";".join(reasons[pos]) for pos in range(len(work)) if reasons[pos]]

    exact_duplicate_mask = valid.duplicated(keep="first")
    exact_duplicates_dropped = int(exact_duplicate_mask.sum())
    valid = valid.loc[~exact_duplicate_mask].copy()

    conflicting = valid.duplicated(BUSINESS_KEY, keep=False)
    if conflicting.any():
        duplicate_groups = valid.loc[conflicting].groupby(BUSINESS_KEY, dropna=False)
        conflict_indices = []
        for _, group in duplicate_groups:
            if len(group.drop(columns=[], errors="ignore").astype("string").drop_duplicates()) > 1:
                conflict_indices.extend(group.index.tolist())
        conflict_indices = sorted(set(conflict_indices))
        if conflict_indices:
            conflict_rows = valid.loc[conflict_indices].copy()
            conflict_rows["rejection_reason"] = "conflicting_duplicate_business_key"
            rejected = pd.concat([rejected, conflict_rows], ignore_index=True)
            valid = valid.drop(index=conflict_indices)

    valid["order_date"] = pd.to_datetime(valid["order_date"]).dt.strftime("%Y-%m-%d")
    for column in ("customer_name", "product_name", "category", "country"):
        valid[column] = valid[column].fillna("Unknown").replace("", "Unknown")
    valid["discount"] = valid["discount"].astype(float)
    valid["quantity"] = valid["quantity"].astype("int64")
    valid["unit_price"] = valid["unit_price"].astype(float)
    valid["sales_amount"] = (valid["quantity"] * valid["unit_price"] * (1 - valid["discount"])).round(2)

    metrics = {
        "input_rows": int(len(frame)),
        "accepted_rows": int(len(valid)),
        "rejected_rows": int(len(rejected)),
        "exact_duplicates_dropped": exact_duplicates_dropped,
        "rejection_reasons": {
            str(reason): int(count)
            for reason, count in rejected["rejection_reason"].str.split(";").explode().value_counts().items()
        } if not rejected.empty else {},
    }
    logger.info("Validation complete: accepted=%d rejected=%d", len(valid), len(rejected))
    return valid, rejected, metrics