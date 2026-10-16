import pytest

from src.config import GcpSettings


def test_gcp_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "sales-demo-123")
    monkeypatch.setenv("GCP_REGION", "us-central1")
    monkeypatch.setenv("GCS_BUCKET", "sales-demo-bucket")
    monkeypatch.setenv("BIGQUERY_DATASET", "sales_elt")
    assert GcpSettings.from_env().dataset_id == "sales_elt"


def test_gcp_settings_fails_when_resource_configuration_is_missing(monkeypatch):
    for name in ("GCP_PROJECT_ID", "GCS_BUCKET", "BIGQUERY_DATASET"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="Set required environment variables"):
        GcpSettings.from_env()


def test_gcp_settings_rejects_invalid_project_identifier():
    with pytest.raises(ValueError, match="Invalid project_id"):
        GcpSettings("Not A Project", "us-central1", "sales-demo-bucket", "sales_elt")