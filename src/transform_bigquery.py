"""Execute repeatable BigQuery staging, dimensional, and fact SQL scripts."""

import logging
from pathlib import Path

from google.cloud import bigquery

from .config import GcpSettings

logger = logging.getLogger(__name__)
SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def render_sql(filename: str, settings: GcpSettings) -> str:
    """Render only validated project/dataset identifiers into SQL templates."""
    if Path(filename).name != filename:
        raise ValueError("SQL filename must be a file in the project's sql directory")
    template = (SQL_DIR / filename).read_text(encoding="utf-8")
    return template.replace("{{project_id}}", settings.project_id).replace("{{dataset_id}}", settings.dataset_id)


def run_transformations(settings: GcpSettings, *, client=None) -> dict:
    """Build staging, dimensions, and fact; fail if warehouse assertions fail."""
    bq = client or bigquery.Client(project=settings.project_id, location=settings.region)
    for script in ("staging_transformations.sql", "create_dimensions.sql", "create_fact_sales.sql"):
        logger.info("Executing BigQuery transformation script %s", script)
        bq.query(render_sql(script, settings), location=settings.region).result()

    assertion_rows = list(
        bq.query(render_sql("data_quality_assertions.sql", settings), location=settings.region).result()
    )
    failed_checks = [
        {"check": row.check_name, "failures": int(row.failures)}
        for row in assertion_rows
        if int(row.failures) > 0
    ]
    if failed_checks:
        raise RuntimeError(f"BigQuery quality assertions failed: {failed_checks}")

    dataset = f"{settings.project_id}.{settings.dataset_id}"
    count_rows = next(
        iter(
            bq.query(
                f"""SELECT
                  (SELECT COUNT(*) FROM `{dataset}.stg_sales`) AS staged_rows,
                  (SELECT COUNT(*) FROM `{dataset}.stg_sales_rejected`) AS rejected_rows,
                  (SELECT COUNT(*) FROM `{dataset}.fact_sales`) AS fact_rows""",
                location=settings.region,
            ).result()
        )
    )
    result = {
        "staged_rows": int(count_rows.staged_rows),
        "rejected_rows": int(count_rows.rejected_rows),
        "fact_rows": int(count_rows.fact_rows),
        "quality_checks": "passed",
    }
    logger.info("BigQuery transformations complete: %s", result)
    return result


def update_ingestion_status(settings: GcpSettings, ingestion_id: str, status: str, *, client=None) -> None:
    """Set the end-to-end status for a previously raw-loaded file."""
    if status not in {"succeeded", "failed"}:
        raise ValueError("status must be succeeded or failed")
    bq = client or bigquery.Client(project=settings.project_id, location=settings.region)
    table = f"`{settings.project_id}.{settings.dataset_id}.pipeline_audit`"
    bq.query(
        f"""UPDATE {table}
        SET status = @status, completed_at = CURRENT_TIMESTAMP()
        WHERE ingestion_id = @ingestion_id""",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("ingestion_id", "STRING", ingestion_id),
            ]
        ),
        location=settings.region,
    ).result()