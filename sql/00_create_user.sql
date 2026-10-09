-- ============================================================================
--  EstateDB  |  00_create_user.sql (PostgreSQL)
--  Create the database and project user.
--  Run this as the postgres superuser in psql or pgAdmin.
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'estatedb') THEN
        CREATE USER estatedb WITH PASSWORD 'estatedb';
    END IF;
END
$$;

-- Create database if not exists (in psql run: CREATE DATABASE estatedb OWNER estatedb;)
-- Note: PostgreSQL does not permit CREATE DATABASE inside a transaction block.
CREATE DATABASE estatedb OWNER estatedb;
GRANT ALL PRIVILEGES ON DATABASE estatedb TO estatedb;

SELECT 'EstateDB PostgreSQL database and user created successfully.' AS status;
