"""Upload immutable source CSV objects to a GCS raw landing zone."""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from google.api_core.exceptions import PreconditionFailed
from google.cloud import storage

from .config import GcpSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UploadedObject:
    uri: str
    object_name: str
    ingestion_id: str
    source_filename: str
    ingestion_timestamp: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upload_raw_file(
    file_path: str | Path,
    settings: GcpSettings,
    *,
    client=None,
    ingestion_time: datetime | None = None,
) -> UploadedObject:
    """Upload without overwriting; identical bytes map to a stable object/id."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Source CSV does not exist: {path}")
    digest = _sha256_file(path)
    timestamp = (ingestion_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
    timestamp_text = timestamp.isoformat(timespec="seconds")
    ingestion_id = digest
    object_name = (
        f"source=sales/ingestion_date={timestamp.date().isoformat()}/"
        f"{path.stem}-{digest[:16]}{path.suffix.lower()}"
    )
    storage_client = client or storage.Client(project=settings.project_id)
    bucket = storage_client.bucket(settings.bucket_name)
    blob = bucket.blob(object_name)
    blob.metadata = {
        "source_filename": path.name,
        "ingestion_timestamp": timestamp_text,
        "ingestion_id": ingestion_id,
        "processing_status": "uploaded",
        "sha256": digest,
    }
    try:
        blob.upload_from_filename(str(path), content_type="text/csv", if_generation_match=0)
    except PreconditionFailed:
        # Re-running identical content is an idempotent success; the generation
        # precondition prevents an accidental object replacement.
        blob.reload()
        if not blob.metadata or blob.metadata.get("ingestion_id") != ingestion_id:
            raise RuntimeError(f"GCS object already exists with different metadata: {object_name}")
        logger.info("Source object already landed; reusing %s", object_name)
    except Exception as exc:
        logger.exception("GCS upload failed for source filename %s", path.name)
        raise RuntimeError(f"Could not upload {path.name} to the configured raw bucket") from exc

    logger.info("Uploaded raw source object %s", object_name)
    return UploadedObject(
        uri=f"gs://{settings.bucket_name}/{object_name}",
        object_name=object_name,
        ingestion_id=ingestion_id,
        source_filename=path.name,
        ingestion_timestamp=timestamp_text,
    )


def set_processing_status(settings: GcpSettings, object_name: str, status: str, *, client=None) -> None:
    """Update non-sensitive object metadata after downstream processing."""
    if status not in {"uploaded", "succeeded", "failed"}:
        raise ValueError("status must be uploaded, succeeded, or failed")
    storage_client = client or storage.Client(project=settings.project_id)
    blob = storage_client.bucket(settings.bucket_name).blob(object_name)
    blob.reload()
    blob.metadata = {**(blob.metadata or {}), "processing_status": status}
    blob.patch()