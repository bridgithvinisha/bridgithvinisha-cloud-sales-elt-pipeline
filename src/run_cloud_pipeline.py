"""Run one file through GCS raw landing and BigQuery raw batch loading."""

import argparse
import logging
from pathlib import Path

from .config import GcpSettings
from .load_to_bigquery import load_raw_csv
from .transform_bigquery import run_transformations, update_ingestion_status
from .upload_to_gcs import set_processing_status, upload_raw_file

logger = logging.getLogger("sales_cloud_pipeline")


def run_cloud_pipeline(input_path: str | Path) -> dict:
    settings = GcpSettings.from_env()
    uploaded = upload_raw_file(input_path, settings)
    try:
        result = load_raw_csv(uploaded, settings)
        transform_result = run_transformations(settings)
        update_ingestion_status(settings, uploaded.ingestion_id, "succeeded")
    except Exception:
        try:
            update_ingestion_status(settings, uploaded.ingestion_id, "failed")
        except Exception:
            logger.exception("Failed to mark BigQuery ingestion status as failed")
        try:
            set_processing_status(settings, uploaded.object_name, "failed")
        except Exception:
            logger.exception("Failed to mark the GCS object status as failed")
        raise
    set_processing_status(settings, uploaded.object_name, "succeeded")
    return {**result, **transform_result, "gcs_uri": uploaded.uri, "source_filename": uploaded.source_filename}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Source CSV file")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        result = run_cloud_pipeline(args.input)
    except Exception:
        logger.exception("Cloud pipeline failed")
        raise
    print(result)


if __name__ == "__main__":
    main()