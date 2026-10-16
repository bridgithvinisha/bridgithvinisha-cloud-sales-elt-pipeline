CREATE TABLE IF NOT EXISTS `{{project_id}}.{{dataset_id}}.raw_sales` (
  order_id STRING,
  order_line_id STRING,
  order_date STRING,
  customer_id STRING,
  customer_name STRING,
  product_id STRING,
  product_name STRING,
  category STRING,
  quantity STRING,
  unit_price STRING,
  discount STRING,
  country STRING,
  source_filename STRING NOT NULL,
  ingestion_id STRING NOT NULL,
  ingested_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS `{{project_id}}.{{dataset_id}}.pipeline_audit` (
  ingestion_id STRING NOT NULL,
  source_filename STRING NOT NULL,
  status STRING NOT NULL,
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  input_rows INT64 NOT NULL,
  error_message STRING
);