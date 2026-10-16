CREATE TABLE IF NOT EXISTS `{{project_id}}.{{dataset_id}}.dim_customer` (
  customer_key STRING NOT NULL,
  customer_id STRING NOT NULL,
  customer_name STRING NOT NULL,
  country STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS `{{project_id}}.{{dataset_id}}.dim_product` (
  product_key STRING NOT NULL,
  product_id STRING NOT NULL,
  product_name STRING NOT NULL,
  category STRING NOT NULL,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS `{{project_id}}.{{dataset_id}}.dim_date` (
  date_key INT64 NOT NULL,
  full_date DATE NOT NULL,
  year INT64 NOT NULL,
  quarter INT64 NOT NULL,
  month INT64 NOT NULL,
  month_name STRING NOT NULL,
  day_of_month INT64 NOT NULL,
  day_of_week INT64 NOT NULL
);

MERGE `{{project_id}}.{{dataset_id}}.dim_customer` AS target
USING (
  SELECT customer_id, customer_name, country
  FROM `{{project_id}}.{{dataset_id}}.stg_sales`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY ingested_at DESC, source_filename DESC) = 1
  UNION DISTINCT SELECT 'UNKNOWN', 'Unknown', 'Unknown'
) AS source
ON target.customer_id = source.customer_id
WHEN MATCHED AND (target.customer_name != source.customer_name OR target.country != source.country)
  THEN UPDATE SET customer_name = source.customer_name, country = source.country, updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT
  (customer_key, customer_id, customer_name, country, created_at, updated_at)
  VALUES (IF(source.customer_id = 'UNKNOWN', 'UNKNOWN', GENERATE_UUID()), source.customer_id,
          source.customer_name, source.country, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

MERGE `{{project_id}}.{{dataset_id}}.dim_product` AS target
USING (
  SELECT product_id, product_name, category
  FROM `{{project_id}}.{{dataset_id}}.stg_sales`
  QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY ingested_at DESC, source_filename DESC) = 1
  UNION DISTINCT SELECT 'UNKNOWN', 'Unknown', 'Unknown'
) AS source
ON target.product_id = source.product_id
WHEN MATCHED AND (target.product_name != source.product_name OR target.category != source.category)
  THEN UPDATE SET product_name = source.product_name, category = source.category, updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT
  (product_key, product_id, product_name, category, created_at, updated_at)
  VALUES (IF(source.product_id = 'UNKNOWN', 'UNKNOWN', GENERATE_UUID()), source.product_id,
          source.product_name, source.category, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

INSERT INTO `{{project_id}}.{{dataset_id}}.dim_date`
  (date_key, full_date, year, quarter, month, month_name, day_of_month, day_of_week)
WITH date_bounds AS (
  SELECT MIN(order_date) AS min_date, MAX(order_date) AS max_date
  FROM `{{project_id}}.{{dataset_id}}.stg_sales`
), calendar AS (
  SELECT full_date
  FROM date_bounds, UNNEST(GENERATE_DATE_ARRAY(min_date, max_date)) AS full_date
)
SELECT
  CAST(FORMAT_DATE('%Y%m%d', full_date) AS INT64), full_date,
  EXTRACT(YEAR FROM full_date), EXTRACT(QUARTER FROM full_date),
  EXTRACT(MONTH FROM full_date), FORMAT_DATE('%B', full_date),
  EXTRACT(DAY FROM full_date), EXTRACT(DAYOFWEEK FROM full_date)
FROM calendar AS source
WHERE NOT EXISTS (
  SELECT 1 FROM `{{project_id}}.{{dataset_id}}.dim_date` AS target
  WHERE target.full_date = source.full_date
);