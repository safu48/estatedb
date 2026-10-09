-- ============================================================================
--  EstateDB  |  01_drop.sql (PostgreSQL)
--  Drops every object so the schema can be rebuilt cleanly from scratch.
-- ============================================================================

-- Stored Procedures & Functions ----------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_inquiry_status(INT, VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS sp_record_sale(INT, INT, NUMERIC, VARCHAR) CASCADE;
DROP PROCEDURE IF EXISTS sp_record_sale CASCADE;
DROP FUNCTION IF EXISTS fn_months_listed(INT) CASCADE;
DROP FUNCTION IF EXISTS fn_agent_total_sales(INT) CASCADE;
DROP FUNCTION IF EXISTS fn_agent_avg_rating(INT) CASCADE;
DROP FUNCTION IF EXISTS fn_property_count(VARCHAR) CASCADE;
DROP FUNCTION IF EXISTS datediff(TIMESTAMP, TIMESTAMP) CASCADE;
DROP FUNCTION IF EXISTS date_add(DATE, INTERVAL) CASCADE;
DROP FUNCTION IF EXISTS date_sub(DATE, INTERVAL) CASCADE;

-- Trigger Functions -----------------------------------------------------------
DROP FUNCTION IF EXISTS fn_trg_properties_after_insert() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_properties_after_update() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_properties_after_delete() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_users_after_insert() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_users_after_update() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_inquiries_after_update() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_txn_after_insert() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_txn_before_insert() CASCADE;
DROP FUNCTION IF EXISTS fn_trg_txn_after_insert_status() CASCADE;

-- Views -----------------------------------------------------------------------
DROP VIEW IF EXISTS v_monthly_sales CASCADE;
DROP VIEW IF EXISTS v_city_stats CASCADE;
DROP VIEW IF EXISTS v_agent_performance CASCADE;
DROP VIEW IF EXISTS v_property_listings CASCADE;

-- Tables (CASCADE cleanly removes foreign key dependencies) --------------------
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS favorites CASCADE;
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS inquiries CASCADE;
DROP TABLE IF EXISTS property_amenities CASCADE;
DROP TABLE IF EXISTS property_images CASCADE;
DROP TABLE IF EXISTS properties CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS amenities CASCADE;
DROP TABLE IF EXISTS property_types CASCADE;
DROP TABLE IF EXISTS cities CASCADE;
DROP TABLE IF EXISTS roles CASCADE;
