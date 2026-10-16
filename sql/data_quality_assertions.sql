-- Execute after staging and fact transformations. Any non-zero result is a
-- failed check; use these queries as an integration-test checklist.
SELECT 'duplicate_fact_grain' AS check_name, COUNT(*) AS failures
FROM (
  SELECT order_id, order_line_id
  FROM `{{project_id}}.{{dataset_id}}.fact_sales`
  GROUP BY order_id, order_line_id
  HAVING COUNT(*) != 1
)
UNION ALL
SELECT 'unmatched_customer' AS check_name, COUNT(*) AS failures
FROM `{{project_id}}.{{dataset_id}}.fact_sales` f
LEFT JOIN `{{project_id}}.{{dataset_id}}.dim_customer` d USING (customer_key)
WHERE d.customer_key IS NULL
UNION ALL
SELECT 'unmatched_product' AS check_name, COUNT(*) AS failures
FROM `{{project_id}}.{{dataset_id}}.fact_sales` f
LEFT JOIN `{{project_id}}.{{dataset_id}}.dim_product` d USING (product_key)
WHERE d.product_key IS NULL
UNION ALL
SELECT 'unmatched_date' AS check_name, COUNT(*) AS failures
FROM `{{project_id}}.{{dataset_id}}.fact_sales` f
LEFT JOIN `{{project_id}}.{{dataset_id}}.dim_date` d USING (date_key)
WHERE d.date_key IS NULL
UNION ALL
SELECT 'invalid_measures' AS check_name, COUNT(*) AS failures
FROM `{{project_id}}.{{dataset_id}}.fact_sales`
WHERE quantity <= 0 OR unit_price < 0 OR discount NOT BETWEEN 0 AND 1
   OR sales_amount != ROUND(quantity * unit_price * (1 - discount), 2);