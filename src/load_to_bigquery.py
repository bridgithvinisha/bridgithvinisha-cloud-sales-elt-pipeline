"""Batch-load GCS CSVs into a typed-as-STRING BigQuery raw table."""

import logging
import uuid
from pathlib import Path

from google.cloud import bigquery

from .config import RAW_SOURCE_COLUMNS, GcpSettings
from .upload_to_gcs import UploadedObject

logger = logging.getLogger(__name__)
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def _table_id(settings: GcpSettings, table_name: str) -> str:
    return f"{settings.project_id}.{settings.dataset_id}.{table_name}"


def load_raw_csv(
    source: UploadedObject,
    settings: GcpSettings,
    *,
    client=None,
) -> dict:
    """Load a file using a batch load job, preserving source values as strings.

    BigQuery staging will use SAFE_CAST to classify malformed values without
    losing the original raw strings. Successful ingestion IDs are skipped on
    rerun, making the file-level operation idempotent.
    """
    bq = client or bigquery.Client(project=settings.project_id, location=settings.region)
    setup_sql = (SQL_DIR / "create_raw_tables.sql").read_text(encoding="utf-8")
    setup_sql = setup_sql.replace("{{project_id}}", settings.project_id).replace("{{dataset_id}}", settings.dataset_id)
    bq.query(setup_sql, location=settings.region).result()

    audit_table = _table_id(settings, "pipeline_audit")
    check = bq.query(
        f"SELECT COUNT(*) AS existing_rows FROM `{_table_id(settings, 'raw_sales')}` WHERE ingestion_id = @ingestion_id",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("ingestion_id", "STRING", source.ingestion_id)]
        ),
        location=settings.region,
    ).result()
    existing = next(iter(check), None)
    if existing and int(existing.existing_rows) > 0:
        logger.info("Raw ingestion %s already exists; skipping duplicate append", source.ingestion_id[:12])
        return {"status": "skipped", "ingestion_id": source.ingestion_id, "loaded_rows": 0}

    temp_name = f"raw_load_{uuid.uuid4().hex}"
    temp_table_id = _table_id(settings, temp_name)
    schema = [bigquery.SchemaField(column, "STRING", mode="NULLABLE") for column in RAW_SOURCE_COLUMNS]
    bq.create_table(bigquery.Table(temp_table_id, schema=schema))
    try:
        load_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=False,
            schema=[bigquery.SchemaField(column, "STRING", mode="NULLABLE") for column in RAW_SOURCE_COLUMNS],
            max_bad_records=0,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        load_job = bq.load_table_from_uri(source.uri, temp_table_id, job_config=load_config, location=settings.region)
        load_job.result()
        loaded_rows = int(load_job.output_rows or 0)
        bq.query(
            f"""
            INSERT INTO `{_table_id(settings, 'raw_sales')}`
              ({', '.join(RAW_SOURCE_COLUMNS)}, source_filename, ingestion_id, ingested_at)
            SELECT {', '.join(RAW_SOURCE_COLUMNS)}, @source_filename, @ingestion_id, @ingested_at
            FROM `{temp_table_id}`
            """,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("source_filename", "STRING", source.source_filename),
                    bigquery.ScalarQueryParameter("ingestion_id", "STRING", source.ingestion_id),
                    bigquery.ScalarQueryParameter("ingested_at", "TIMESTAMP", source.ingestion_timestamp),
                ]
            ),
            location=settings.region,
        ).result()
        bq.query(
            f"""INSERT INTO `{audit_table}`
            (ingestion_id, source_filename, status, started_at, completed_at, input_rows, error_message)
            VALUES (@ingestion_id, @source_filename, 'loaded', @started_at, CURRENT_TIMESTAMP(), @input_rows, NULL)""",
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("ingestion_id", "STRING", source.ingestion_id),
                    bigquery.ScalarQueryParameter("source_filename", "STRING", source.source_filename),
                    bigquery.ScalarQueryParameter("started_at", "TIMESTAMP", source.ingestion_timestamp),
                    bigquery.ScalarQueryParameter("input_rows", "INT64", loaded_rows),
                ]
            ),
            location=settings.region,
        ).result()
        logger.info("Loaded %d rows for ingestion %s", loaded_rows, source.ingestion_id[:12])
        return {"status": "succeeded", "ingestion_id": source.ingestion_id, "loaded_rows": loaded_rows}
    except Exception as exc:
        logger.exception("BigQuery batch load failed for ingestion %s", source.ingestion_id[:12])
        try:
            bq.query(
                f"""INSERT INTO `{audit_table}`
                (ingestion_id, source_filename, status, started_at, completed_at, input_rows, error_message)
                VALUES (@ingestion_id, @source_filename, 'failed', @started_at, CURRENT_TIMESTAMP(), 0, @error_message)""",
                job_config=bigquery.QueryJobConfig(
                    query_parameters=[
                        bigquery.ScalarQueryParameter("ingestion_id", "STRING", source.ingestion_id),
                        bigquery.ScalarQueryParameter("source_filename", "STRING", source.source_filename),
                        bigquery.ScalarQueryParameter("started_at", "TIMESTAMP", source.ingestion_timestamp),
                        bigquery.ScalarQueryParameter("error_message", "STRING", type(exc).__name__),
                    ]
                ),
                location=settings.region,
            ).result()
        except Exception:
            logger.exception("Could not record the failed load in pipeline audit")
        raise RuntimeError("BigQuery raw load failed; see the job details and pipeline audit") from exc
    finally:
        bq.delete_table(temp_table_id, not_found_ok=True)