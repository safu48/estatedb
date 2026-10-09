-- ============================================================================
--  EstateDB  |  04_views.sql
--  Views that pre-join / pre-aggregate data for the application:
--    * v_property_listings : denormalised listing row (joins + scalar sub-queries)
--    * v_agent_performance : per-agent KPIs (correlated aggregate sub-queries)
--    * v_city_stats        : per-city aggregates (LEFT JOIN + GROUP BY)
--    * v_monthly_sales     : sales grouped by month (GROUP BY on TO_CHAR)
-- ============================================================================

-- One tidy row per property, with type, city, agent, cover image and counts.
CREATE OR REPLACE VIEW v_property_listings AS
SELECT p.property_id,
       p.title,
       p.price,
       p.bedrooms,
       p.bathrooms,
       p.area_sqft,
       p.year_built,
       p.address,
       p.listing_type,
       p.status,
       p.featured,
       p.created_at,
       pt.type_id,
       pt.type_name,
       c.city_id,
       c.city_name,
       c.state,
       a.agent_id,
       u.full_name  AS agent_name,
       u.phone      AS agent_phone,
       u.email      AS agent_email,
       (SELECT pi.image_url
          FROM property_images pi
         WHERE pi.property_id = p.property_id
           AND pi.is_primary = 'Y'
         LIMIT 1)                                 AS primary_image,
       (SELECT COUNT(*) FROM favorites f
         WHERE f.property_id = p.property_id)     AS favorite_count,
       (SELECT COUNT(*) FROM property_amenities pa
         WHERE pa.property_id = p.property_id)    AS amenity_count
  FROM properties p
  JOIN property_types pt ON pt.type_id  = p.type_id
  JOIN cities         c  ON c.city_id   = p.city_id
  JOIN agents         a  ON a.agent_id  = p.agent_id
  JOIN users          u  ON u.user_id   = a.agent_id;

-- Key performance indicators for every agent.
CREATE OR REPLACE VIEW v_agent_performance AS
SELECT a.agent_id,
       u.full_name       AS agent_name,
       u.email,
       u.phone,
       a.agency_name,
       a.commission_rate,
       a.hire_date,
       (SELECT COUNT(*) FROM properties p
         WHERE p.agent_id = a.agent_id)                          AS total_listings,
       (SELECT COUNT(*) FROM properties p
         WHERE p.agent_id = a.agent_id
           AND p.status IN ('SOLD', 'RENTED'))                   AS closed_listings,
       (SELECT COALESCE(SUM(t.sale_price), 0) FROM transactions t
         WHERE t.agent_id = a.agent_id)                          AS total_sales_value,
       (SELECT COALESCE(SUM(t.commission_amount), 0) FROM transactions t
         WHERE t.agent_id = a.agent_id)                          AS total_commission,
       (SELECT COUNT(*) FROM reviews r
         WHERE r.agent_id = a.agent_id)                          AS review_count,
       (SELECT ROUND(AVG(r.rating)::numeric, 2) FROM reviews r
         WHERE r.agent_id = a.agent_id)                          AS avg_rating
  FROM agents a
  JOIN users u ON u.user_id = a.agent_id;

-- Aggregate market stats per city (LEFT JOIN keeps cities with 0 listings).
CREATE OR REPLACE VIEW v_city_stats AS
SELECT c.city_id,
       c.city_name,
       c.state,
       COUNT(p.property_id)                                      AS property_count,
       COALESCE(ROUND(AVG(p.price)::numeric, 2), 0)              AS avg_price,
       COALESCE(MIN(p.price), 0)                                 AS min_price,
       COALESCE(MAX(p.price), 0)                                 AS max_price,
       SUM(CASE WHEN p.status = 'AVAILABLE' THEN 1 ELSE 0 END)   AS available_count
  FROM cities c
  LEFT JOIN properties p ON p.city_id = c.city_id
 GROUP BY c.city_id, c.city_name, c.state;

-- Deal volume and revenue grouped by calendar month.
CREATE OR REPLACE VIEW v_monthly_sales AS
SELECT TO_CHAR(t.txn_date, 'YYYY-MM') AS sales_month,
       COUNT(*)                       AS deal_count,
       SUM(t.sale_price)              AS revenue,
       SUM(t.commission_amount)       AS commission,
       ROUND(AVG(t.sale_price)::numeric, 2) AS avg_deal
  FROM transactions t
 GROUP BY TO_CHAR(t.txn_date, 'YYYY-MM');
