-- ============================================================================
--  EstateDB  |  run_all.sql   --   master build script for PostgreSQL
--
--  Usage in PostgreSQL CLI (psql):
--      psql -U estatedb -d estatedb -f sql/run_all.sql
--  Or within psql console:
--      \c estatedb
--      \i sql/run_all.sql
--
--  Or run through Python without needing CLI tools:
--      python scripts/init_db.py
-- ============================================================================

\echo '==== 1/6 Dropping existing objects ===='
\i sql/01_drop.sql

\echo '==== 2/6 Creating tables, constraints, indexes ===='
\i sql/02_tables.sql

\echo '==== 3/6 Creating triggers ===='
\i sql/03_triggers.sql

\echo '==== 4/6 Creating views ===='
\i sql/04_views.sql

\echo '==== 5/6 Creating stored procedures & functions ===='
\i sql/05_procedures.sql

\echo '==== 6/6 Loading seed data ===='
\i sql/06_seed.sql

\echo '==== EstateDB PostgreSQL build complete ===='
