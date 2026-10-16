"""Configuration and canonical column definitions for the local pipeline."""

import os
import re
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

REQUIRED_COLUMNS = (
    "order_id",
    "order_line_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
)

OPTIONAL_COLUMNS = (
    "customer_name",
    "product_name",
    "category",
    "discount",
    "country",
)

OUTPUT_COLUMNS = (
    "order_id",
    "order_line_id",
    "order_date",
    "customer_id",
    "customer_name",
    "product_id",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "discount",
    "country",
    "sales_amount",
)

RAW_SOURCE_COLUMNS = (
    "order_id",
    "order_line_id",
    "order_date",
    "customer_id",
    "customer_name",
    "product_id",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "discount",
    "country",
)


@dataclass(frozen=True)
class GcpSettings:
    """Non-secret cloud resource identifiers, sourced from environment vars."""

    project_id: str
    region: str
    bucket_name: str
    dataset_id: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]{4,28}[a-z0-9]", self.project_id):
            raise ValueError("Invalid project_id: use 6-30 lowercase letters, numbers, or hyphens")
        if not re.fullmatch(r"[A-Za-z0-9_]+", self.dataset_id):
            raise ValueError("Invalid dataset_id: use only letters, numbers, and underscores")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]", self.bucket_name):
            raise ValueError("Invalid GCS bucket name")
        if not re.fullmatch(r"[A-Za-z0-9-]+", self.region):
            raise ValueError("Invalid GCP_REGION")

    @classmethod
    def from_env(cls) -> "GcpSettings":
        values = {
            "project_id": os.getenv("GCP_PROJECT_ID", "").strip(),
            "region": os.getenv("GCP_REGION", "us-central1").strip(),
            "bucket_name": os.getenv("GCS_BUCKET", "").strip(),
            "dataset_id": os.getenv("BIGQUERY_DATASET", "").strip(),
        }
        missing = [name for name in ("project_id", "bucket_name", "dataset_id") if not values[name]]
        if missing:
            raise ValueError(f"Set required environment variables: {', '.join(missing)}")
        return cls(**values)