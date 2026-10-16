-- Keep the original string-valued raw_sales table unchanged. Invalid records
-- and conflicting (order_id, order_line_id) versions are retained in the
-- quarantine table with a reason; valid business keys are deduplicated.
CREATE OR REPLACE TABLE `{{project_id}}.{{dataset_id}}.stg_sales_rejected` AS
WITH typed AS (
  SELECT
    order_id, order_line_id,
    SAFE_CAST(order_date AS DATE) AS order_date,
    customer_id, customer_name, product_id, product_name, category,
    SAFE_CAST(quantity AS INT64) AS quantity,
    SAFE_CAST(unit_price AS NUMERIC) AS unit_price,
    discount AS raw_discount,
    COALESCE(SAFE_CAST(NULLIF(TRIM(discount), '') AS NUMERIC), 0) AS discount,
    country, source_filename, ingestion_id, ingested_at
  FROM `{{project_id}}.{{dataset_id}}.raw_sales`
), conflicting_keys AS (
  SELECT order_id, order_line_id
  FROM typed
  GROUP BY order_id, order_line_id
  HAVING COUNT(DISTINCT TO_JSON_STRING(STRUCT(
    order_date, customer_id, customer_name, product_id, product_name, category,
    quantity, unit_price, discount, country
  ))) > 1
), classified AS (
  SELECT
    t.*,
    ARRAY_TO_STRING(ARRAY(
      SELECT reason FROM UNNEST([
        IF(order_id IS NULL OR TRIM(order_id) = '', 'missing_order_id', NULL),
        IF(order_line_id IS NULL OR TRIM(order_line_id) = '', 'missing_order_line_id', NULL),
        IF(order_date IS NULL, 'invalid_order_date', NULL),
        IF(customer_id IS NULL OR TRIM(customer_id) = '', 'missing_customer_id', NULL),
        IF(product_id IS NULL OR TRIM(product_id) = '', 'missing_product_id', NULL),
        IF(quantity IS NULL, 'invalid_quantity', NULL),
        IF(quantity <= 0, 'non_positive_quantity', NULL),
        IF(unit_price IS NULL, 'invalid_unit_price', NULL),
        IF(unit_price < 0, 'negative_unit_price', NULL),
          IF(NULLIF(TRIM(raw_discount), '') IS NOT NULL
            AND SAFE_CAST(TRIM(raw_discount) AS NUMERIC) IS NULL, 'invalid_discount', NULL),
        IF(discount < 0 OR discount > 1, 'discount_out_of_range', NULL),
        IF(c.order_id IS NOT NULL, 'conflicting_duplicate_business_key', NULL)
      ]) AS reason
      WHERE reason IS NOT NULL
    ), ';') AS rejection_reason
  FROM typed AS t
  LEFT JOIN conflicting_keys AS c USING (order_id, order_line_id)
)
SELECT * FROM classified WHERE rejection_reason != '';

CREATE OR REPLACE TABLE `{{project_id}}.{{dataset_id}}.stg_sales` AS
WITH typed AS (
  SELECT
    order_id, order_line_id,
    SAFE_CAST(order_date AS DATE) AS order_date,
    customer_id, COALESCE(NULLIF(TRIM(customer_name), ''), 'Unknown') AS customer_name,
    product_id, COALESCE(NULLIF(TRIM(product_name), ''), 'Unknown') AS product_name,
    COALESCE(NULLIF(TRIM(category), ''), 'Unknown') AS category,
    SAFE_CAST(quantity AS INT64) AS quantity,
    SAFE_CAST(unit_price AS NUMERIC) AS unit_price,
    discount AS raw_discount,
    COALESCE(SAFE_CAST(NULLIF(TRIM(discount), '') AS NUMERIC), 0) AS discount,
    COALESCE(NULLIF(TRIM(country), ''), 'Unknown') AS country,
    source_filename, ingestion_id, ingested_at
  FROM `{{project_id}}.{{dataset_id}}.raw_sales`
), conflicting_keys AS (
  SELECT order_id, order_line_id
  FROM typed
  GROUP BY order_id, order_line_id
  HAVING COUNT(DISTINCT TO_JSON_STRING(STRUCT(
    order_date, customer_id, customer_name, product_id, product_name, category,
    quantity, unit_price, discount, country
  ))) > 1
)
SELECT
  order_id, order_line_id, order_date, customer_id, customer_name,
  product_id, product_name, category, quantity, unit_price, discount, country,
  ROUND(quantity * unit_price * (1 - discount), 2) AS sales_amount,
  source_filename, ingestion_id, ingested_at
FROM typed AS t
WHERE order_id IS NOT NULL AND TRIM(order_id) != ''
  AND order_line_id IS NOT NULL AND TRIM(order_line_id) != ''
  AND order_date IS NOT NULL
  AND customer_id IS NOT NULL AND TRIM(customer_id) != ''
  AND product_id IS NOT NULL AND TRIM(product_id) != ''
  AND quantity > 0 AND unit_price >= 0 AND discount BETWEEN 0 AND 1
  AND (NULLIF(TRIM(raw_discount), '') IS NULL OR SAFE_CAST(TRIM(raw_discount) AS NUMERIC) IS NOT NULL)
  AND NOT EXISTS (
    SELECT 1 FROM conflicting_keys AS c
    WHERE c.order_id = t.order_id AND c.order_line_id = t.order_line_id
  )
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY order_id, order_line_id
  ORDER BY ingested_at DESC, ingestion_id DESC
) = 1;