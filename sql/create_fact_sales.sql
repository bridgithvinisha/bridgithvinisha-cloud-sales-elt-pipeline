CREATE TABLE IF NOT EXISTS `{{project_id}}.{{dataset_id}}.fact_sales` (
  sales_key STRING NOT NULL,
  order_id STRING NOT NULL,
  order_line_id STRING NOT NULL,
  date_key INT64 NOT NULL,
  customer_key STRING NOT NULL,
  product_key STRING NOT NULL,
  quantity INT64 NOT NULL,
  unit_price NUMERIC NOT NULL,
  discount NUMERIC NOT NULL,
  sales_amount NUMERIC NOT NULL,
  source_filename STRING NOT NULL,
  ingestion_id STRING NOT NULL,
  ingested_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

MERGE `{{project_id}}.{{dataset_id}}.fact_sales` AS target
USING (
  SELECT
    TO_HEX(SHA256(TO_JSON_STRING(STRUCT(s.order_id, s.order_line_id)))) AS sales_key,
    s.order_id, s.order_line_id,
    CAST(FORMAT_DATE('%Y%m%d', s.order_date) AS INT64) AS date_key,
    COALESCE(c.customer_key, 'UNKNOWN') AS customer_key,
    COALESCE(p.product_key, 'UNKNOWN') AS product_key,
    s.quantity, s.unit_price, s.discount, s.sales_amount,
    s.source_filename, s.ingestion_id, s.ingested_at
  FROM `{{project_id}}.{{dataset_id}}.stg_sales` AS s
  LEFT JOIN `{{project_id}}.{{dataset_id}}.dim_customer` AS c USING (customer_id)
  LEFT JOIN `{{project_id}}.{{dataset_id}}.dim_product` AS p USING (product_id)
  LEFT JOIN `{{project_id}}.{{dataset_id}}.dim_date` AS d ON d.full_date = s.order_date
  WHERE d.date_key IS NOT NULL
) AS source
ON target.sales_key = source.sales_key
WHEN MATCHED AND (
  target.quantity != source.quantity OR target.unit_price != source.unit_price
  OR target.discount != source.discount OR target.sales_amount != source.sales_amount
  OR target.customer_key != source.customer_key OR target.product_key != source.product_key
) THEN UPDATE SET
  date_key = source.date_key, customer_key = source.customer_key,
  product_key = source.product_key, quantity = source.quantity,
  unit_price = source.unit_price, discount = source.discount,
  sales_amount = source.sales_amount, source_filename = source.source_filename,
  ingestion_id = source.ingestion_id, ingested_at = source.ingested_at,
  updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
  sales_key, order_id, order_line_id, date_key, customer_key, product_key,
  quantity, unit_price, discount, sales_amount, source_filename, ingestion_id,
  ingested_at, created_at, updated_at
) VALUES (
  source.sales_key, source.order_id, source.order_line_id, source.date_key,
  source.customer_key, source.product_key, source.quantity, source.unit_price,
  source.discount, source.sales_amount, source.source_filename,
  source.ingestion_id, source.ingested_at, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP()
);