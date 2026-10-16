# Local source and output schema

| Field | Type | Meaning / rule |
|---|---|---|
| order_id | string | Source order identifier; not unique because orders can have multiple lines. |
| order_line_id | string | Line identifier within an order. |
| order_date | date | Valid calendar date, normalized to `YYYY-MM-DD`. |
| customer_id | string | Customer natural key from the source. |
| customer_name | string | Optional descriptive label; missing values become `Unknown`. |
| product_id | string | Product natural key from the source. |
| product_name | string | Optional descriptive label; missing values become `Unknown`. |
| category | string | Optional product grouping; missing values become `Unknown`. |
| quantity | integer | Must be a positive whole-number quantity. |
| unit_price | decimal | Must be numeric and non-negative. |
| discount | decimal | Fraction in the inclusive range 0–1; missing defaults to zero; malformed non-empty text is rejected. |
| country | string | Optional geography; missing values become `Unknown`. |
| sales_amount | decimal | `quantity * unit_price * (1 - discount)`, rounded to 2 decimal places. |

The local business key/grain is one row per `(order_id, order_line_id)`. Exact
duplicate rows retain the first copy. Conflicting rows with the same business
key are quarantined together because the source does not identify a trustworthy
winner. `order_id` alone is not a duplicate key.