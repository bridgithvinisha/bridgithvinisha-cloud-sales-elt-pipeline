"""Run the local extract, validate, transform, and quality-report pipeline."""

import argparse
import json
import logging
from pathlib import Path

from .extract import profile_dataframe, read_sales_csv
from .transform import select_output_columns
from .validate import validate_and_clean

logger = logging.getLogger("sales_pipeline")


def run_pipeline(input_path: str | Path, output_dir: str | Path) -> dict:
    """Process one CSV, preserving input and replacing deterministic outputs."""
    source = Path(input_path)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    raw = read_sales_csv(source)
    profile = profile_dataframe(raw)
    clean, rejected, metrics = validate_and_clean(raw)
    clean = select_output_columns(clean)

    clean_path = destination / "cleaned_sales.csv"
    rejected_path = destination / "rejected_sales.csv"
    summary_path = destination / "quality_summary.json"
    clean.to_csv(clean_path, index=False)
    rejected.to_csv(rejected_path, index=False)
    summary = {
        "source_file": source.name,
        "profile": profile,
        "validation": metrics,
        "accepted_sales_amount": round(float(clean["sales_amount"].sum()), 2),
        "outputs": {
            "cleaned_csv": clean_path.name,
            "rejected_csv": rejected_path.name,
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Pipeline finished for %s", source.name)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Path to an input sales CSV")
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        summary = run_pipeline(args.input, args.output_dir)
    except Exception:
        logger.exception("Pipeline failed")
        raise
    print(json.dumps(summary["validation"], indent=2))


if __name__ == "__main__":
    main()