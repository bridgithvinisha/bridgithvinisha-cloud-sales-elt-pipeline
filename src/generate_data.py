"""Generate deterministic synthetic sales CSV data for local development."""

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd


def generate_sales_data(row_count: int = 120, seed: int = 42) -> pd.DataFrame:
    """Return reproducible, explicitly synthetic order-line data."""
    if row_count < 1:
        raise ValueError("row_count must be at least 1")

    rng = random.Random(seed)
    customers = [("C001", "Avery Chen"), ("C002", "Jordan Patel"), ("C003", "Morgan Lee")]
    products = [
        ("P001", "Wireless Mouse", "Accessories", 19.99),
        ("P002", "Notebook", "Stationery", 4.50),
        ("P003", "Desk Lamp", "Home Office", 32.00),
        ("P004", "USB-C Cable", "Accessories", 9.25),
    ]
    countries = ["United States", "Canada", "United Kingdom"]
    first_day = date(2025, 1, 1)
    rows = []
    for index in range(row_count):
        customer_id, customer_name = rng.choice(customers)
        product_id, product_name, category, unit_price = rng.choice(products)
        order_number = index // 2 + 1
        rows.append(
            {
                "order_id": f"ORD-{order_number:05d}",
                "order_line_id": f"{index % 2 + 1:03d}",
                "order_date": (first_day + timedelta(days=rng.randrange(365))).isoformat(),
                "customer_id": customer_id,
                "customer_name": customer_name,
                "product_id": product_id,
                "product_name": product_name,
                "category": category,
                "quantity": rng.randint(1, 5),
                "unit_price": unit_price,
                "discount": rng.choice([0.0, 0.0, 0.05, 0.10]),
                "country": rng.choice(countries),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/sales_synthetic.csv"))
    parser.add_argument("--rows", type=int, default=120)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    generate_sales_data(args.rows, args.seed).to_csv(args.output, index=False)
    print(f"Wrote {args.rows} synthetic rows to {args.output}")


if __name__ == "__main__":
    main()