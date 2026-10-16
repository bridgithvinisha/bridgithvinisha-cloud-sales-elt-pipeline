-- Monthly revenue and order counts (order_id, not line count).
SELECT d.year, d.month, d.month_name,
       ROUND(SUM(f.sales_amount), 2) AS revenue,
       COUNT(DISTINCT f.order_id) AS order_count
FROM `{{project_id}}.{{dataset_id}}.fact_sales` AS f
JOIN `{{project_id}}.{{dataset_id}}.dim_date` AS d USING (date_key)
GROUP BY d.year, d.month, d.month_name
ORDER BY d.year, d.month;

-- Top products by net sales.
SELECT p.product_id, p.product_name, p.category,
       SUM(f.quantity) AS units_sold,
       ROUND(SUM(f.sales_amount), 2) AS revenue
FROM `{{project_id}}.{{dataset_id}}.fact_sales` AS f
JOIN `{{project_id}}.{{dataset_id}}.dim_product` AS p USING (product_key)
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC
LIMIT 10;

-- Category performance by month.
SELECT d.year, d.month, p.category,
       ROUND(SUM(f.sales_amount), 2) AS revenue,
       SUM(f.quantity) AS units_sold
FROM `{{project_id}}.{{dataset_id}}.fact_sales` AS f
JOIN `{{project_id}}.{{dataset_id}}.dim_product` AS p USING (product_key)
JOIN `{{project_id}}.{{dataset_id}}.dim_date` AS d USING (date_key)
GROUP BY d.year, d.month, p.category
ORDER BY d.year, d.month, revenue DESC;

-- Customer purchasing frequency and average order value.
WITH customer_orders AS (
  SELECT f.customer_key, f.order_id, SUM(f.sales_amount) AS order_value
  FROM `{{project_id}}.{{dataset_id}}.fact_sales` AS f
  GROUP BY f.customer_key, f.order_id
)
SELECT c.customer_id, c.customer_name,
       COUNT(*) AS order_count,
       ROUND(SUM(co.order_value), 2) AS lifetime_revenue,
       ROUND(AVG(co.order_value), 2) AS average_order_value
FROM customer_orders AS co
JOIN `{{project_id}}.{{dataset_id}}.dim_customer` AS c USING (customer_key)
GROUP BY c.customer_id, c.customer_name
ORDER BY lifetime_revenue DESC;

-- Rank products within category using a window function.
WITH category_products AS (
  SELECT p.category, p.product_name, SUM(f.sales_amount) AS revenue
  FROM `{{project_id}}.{{dataset_id}}.fact_sales` AS f
  JOIN `{{project_id}}.{{dataset_id}}.dim_product` AS p USING (product_key)
  GROUP BY p.category, p.product_name
)
SELECT category, product_name, ROUND(revenue, 2) AS revenue,
       RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS category_rank
FROM category_products
QUALIFY category_rank <= 3
ORDER BY category, category_rank;

-- Quality and reconciliation summary for the latest raw ingestion.
SELECT a.ingestion_id, a.source_filename, a.status, a.input_rows,
       (SELECT COUNT(*) FROM `{{project_id}}.{{dataset_id}}.raw_sales` r
        WHERE r.ingestion_id = a.ingestion_id) AS raw_rows,
       (SELECT COUNT(*) FROM `{{project_id}}.{{dataset_id}}.stg_sales` s
        WHERE s.ingestion_id = a.ingestion_id) AS accepted_stage_rows,
       (SELECT COUNT(*) FROM `{{project_id}}.{{dataset_id}}.stg_sales_rejected` q
        WHERE q.ingestion_id = a.ingestion_id) AS quarantined_stage_rows
FROM `{{project_id}}.{{dataset_id}}.pipeline_audit` AS a
QUALIFY ROW_NUMBER() OVER (PARTITION BY ingestion_id ORDER BY started_at DESC) = 1
ORDER BY started_at DESC;