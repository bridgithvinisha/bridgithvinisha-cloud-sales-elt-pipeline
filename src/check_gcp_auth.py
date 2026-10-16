"""Verify that Application Default Credentials can be discovered locally."""

import logging

import google.auth
from google.auth.exceptions import DefaultCredentialsError

from .config import GcpSettings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = GcpSettings.from_env()
    try:
        credentials, detected_project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    except DefaultCredentialsError as exc:
        raise SystemExit(
            "ADC not found. Install gcloud and run `gcloud auth application-default login`."
        ) from exc
    logging.info(
        "ADC discovered (valid=%s); configured project=%s; ADC project=%s",
        credentials.valid,
        settings.project_id,
        detected_project or "not provided",
    )
    logging.info("This check discovers credentials; it does not verify IAM permissions or billing.")


if __name__ == "__main__":
    main()