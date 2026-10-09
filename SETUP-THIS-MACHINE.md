# Setup on this Machine (PostgreSQL)

Target: **PostgreSQL** (local or remote, e.g., Render Managed PostgreSQL), connected via `psycopg[binary,pool]`.

The schema has been migrated to standard PostgreSQL:
- All 14 tables with `SERIAL` / `BIGSERIAL` primary keys, `DECIMAL`, `TIMESTAMP`, foreign keys with cascading where appropriate.
- 9 PL/pgSQL Triggers (7 audit triggers + auto-commission + auto status updates).
- 4 Views (`v_property_listings`, `v_agent_performance`, `v_city_stats`, `v_monthly_sales`).
- 6 Stored routines: 4 stored functions (`fn_agent_total_sales`, `fn_agent_avg_rating`, `fn_property_count`, `fn_months_listed`) and 2 stored procedures (`sp_record_sale`, `sp_update_inquiry_status`).
- Seed data with 24 properties, 9 users, 4 agents, 15 inquiries, 6 transactions, and automatic audit logging.

---

## Quick Start (3 Steps)

### Step 1 — Start or Connect to PostgreSQL
Ensure PostgreSQL is running locally (e.g., standard PostgreSQL on port 5432) or have your Render/cloud PostgreSQL URL ready.

---

### Step 2 — Initialize the Database
Open PowerShell in the project directory:

```powershell
.\.venv\Scripts\python.exe scripts/init_db.py
```

This will:
1. Connect using `DATABASE_URL` (or `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` from `.env`).
2. Run `01_drop.sql` through `06_seed.sql` in order.
3. Synchronize all `SERIAL` sequence values.
4. Verify table, trigger, view, and procedure counts, and print seeded row counts.

> **On Render:** Database tables and seeds are initialized automatically on application startup via the FastAPI lifespan hook (`auto_init_if_needed()`).

---

### Step 3 — Run the Web Application

```powershell
.\.venv\Scripts\python.exe run.py
```

Open your browser to:
**[http://localhost:8000](http://localhost:8000)**

---

## Demo Accounts

| Role | Username | Password | Notes |
|---|---|---|---|
| **Admin** | `admin` | `Admin@123` | Full access to user management, lookups, audit logs, and SQL showcase (`/admin`, `/database`) |
| **Agent** | `sarah` | `Agent@123` | Agent dashboard, listing editor, inquiry workflows, deal recording (`/agent`) |
| **Customer** | `john` | `User@123` | Property searching, favoriting, inquiry submission, writing reviews (`/me`) |

---

## Configuration (`.env`)

The project uses `.env` in the root directory:

```ini
# Render provides DATABASE_URL automatically.
# DATABASE_URL=postgresql://postgres:password@localhost:5432/estatedb

# Or individual parameters for local development:
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=estatedb

SECRET_KEY=b9ce1bf8-c703-4f9e-a0e2-632bba8eeb4a
```

---

## Verification & Developer Utilities

All helper scripts work out-of-the-box with the Python virtual environment:

- **Smoke Test** (tests all 32 pages and routes):
  ```powershell
  .\.venv\Scripts\python.exe scripts/smoke_test.py
  ```
- **Template Syntax Check** (compiles all 32 Jinja templates):
  ```powershell
  .\.venv\Scripts\python.exe scripts/check_templates.py
  ```
- **Link & Route Validator** (validates 78 internal links):
  ```powershell
  .\.venv\Scripts\python.exe scripts/check_links.py
  ```
- **Database Viewer** (view tables & run custom SQL):
  ```powershell
  .\.venv\Scripts\python.exe scripts/db_viewer.py
  .\.venv\Scripts\python.exe scripts/db_viewer.py properties
  .\.venv\Scripts\python.exe scripts/db_viewer.py "SELECT * FROM v_agent_performance"
  ```
