from datetime import datetime, timezone

from src.config import GcpSettings
from src.upload_to_gcs import upload_raw_file


class FakeBlob:
    def __init__(self):
        self.metadata = None
        self.upload_args = None

    def upload_from_filename(self, filename, **kwargs):
        self.upload_args = (filename, kwargs)


class FakeBucket:
    def __init__(self, blob):
        self._blob = blob

    def blob(self, name):
        self.object_name = name
        return self._blob


class FakeStorageClient:
    def __init__(self, blob):
        self._bucket = FakeBucket(blob)

    def bucket(self, name):
        self.bucket_name = name
        return self._bucket


def test_upload_uses_dated_content_addressed_object_and_metadata(tmp_path):
    source = tmp_path / "orders.csv"
    source.write_text("order_id,quantity\nO1,2\n", encoding="utf-8")
    blob = FakeBlob()
    client = FakeStorageClient(blob)
    settings = GcpSettings("sales-demo-123", "us-central1", "sales-demo-bucket", "sales_elt")

    uploaded = upload_raw_file(
        source,
        settings,
        client=client,
        ingestion_time=datetime(2025, 4, 3, tzinfo=timezone.utc),
    )

    assert uploaded.uri.startswith("gs://sales-demo-bucket/source=sales/ingestion_date=2025-04-03/")
    assert uploaded.source_filename == "orders.csv"
    assert uploaded.ingestion_id == blob.metadata["sha256"]
    assert blob.metadata["processing_status"] == "uploaded"
    assert blob.upload_args[1]["if_generation_match"] == 0