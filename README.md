# EstateDB — a real-estate website built around a PostgreSQL database

A full-stack property-listing web application (FastAPI + Jinja2 + PostgreSQL via Psycopg 3) designed for deployment on **Render** with **GitHub**. The web app is modern and responsive, built around handwritten SQL without any ORM to demonstrate database techniques. The `/database` page runs 27 representative statements side by side with their live results.

**14 tables · 9 triggers · 4 views · 4 stored functions · 2 stored procedures · 11 indexes · 235 seed rows**

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/safu48/estatedb)

---

## Contents

1. [Requirements](#1-requirements)
2. [Local Setup](#2-local-setup)
3. [Hosting with GitHub and Render](#3-hosting-with-github-and-render)
4. [Demo Logins](#4-demo-logins)
5. [The Database Schema](#5-the-database-schema)
6. [SQL Techniques & Architecture](#6-sql-techniques--architecture)
7. [Project Layout](#7-project-layout)
8. [Troubleshooting](#8-troubleshooting)
9. [Automated Verification](#9-automated-verification)

---

## 1. Requirements

| Component | Version | Notes |
|---|---|---|
| PostgreSQL | **14+ / 15+ / 16+** | Supported locally or via managed cloud (Render, Neon, Supabase). |
| Python | **3.10+** (3.11 / 3.12 / 3.14 recommended) | Connects via `psycopg[binary,pool]` (Psycopg 3). |
| Git | any | For pushing to GitHub and continuous deployment to Render. |

---

## 2. Local Setup

### Step 1 — Python Virtual Environment

```bash
python -m venv .venv
```

Activate the virtual environment:
- **Windows (PowerShell)**: `.venv\Scripts\Activate.ps1`
- **Windows (CMD)**: `.venv\Scripts\activate.bat`
- **macOS / Linux**: `source .venv/bin/activate`

Install dependencies:
```bash
pip install -r requirements.txt
```

### Step 2 — Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` to match your local or cloud PostgreSQL credentials:
```ini
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=estatedb
DB_SSL=false
```
*(Or specify `DATABASE_URL=postgresql://user:pass@host:5432/estatedb` directly).*

### Step 3 — Initialize Database

Run the automated migration and seed script:
```bash
python scripts/init_db.py
```
*(Or in psql: `psql -U postgres -d estatedb -f sql/run_all.sql`).*

### Step 4 — Run the Web App

```bash
python run.py
```
Open **http://localhost:8000** in your browser.

---

## 3. Hosting with GitHub and Render

EstateDB comes pre-configured with a Render Blueprint (`render.yaml`) that automatically provisions both a **FastAPI Web Service** and a **free managed PostgreSQL database**.

### Step 1 — Push to GitHub

1. Create a new repository on [GitHub](https://github.com/new) (e.g. `estatedb`).
2. Add your GitHub remote and push:
   ```bash
   git add .
   git commit -m "Migrate to PostgreSQL and configure Render hosting"
   git branch -M main
   git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
   git push -u origin main
   ```

### Step 2 — Deploy on Render via Blueprint (Recommended)

1. Sign up or log in at [Render.com](https://render.com).
2. In the Render Dashboard, click **New +** and select **Blueprint**.
3. Connect your GitHub account and choose your `estatedb` repository.
4. Render will read `render.yaml` and show:
   - **estatedb-pg** (Free PostgreSQL Database)
   - **estatedb** (Python Web Service)
5. Click **Apply**.
6. Render will automatically:
   - Provision the PostgreSQL database.
   - Inject the connection string as `DATABASE_URL`.
   - Install dependencies (`pip install -r requirements.txt`).
   - Auto-initialize the schema and seed data on first launch via the application lifespan hook.
   - Start the web server with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Step 3 — Alternative Manual Deploy on Render

If you prefer to configure services manually without Blueprints:

1. **Create PostgreSQL Database on Render**:
   - Click **New +** &rarr; **PostgreSQL**.
   - Name: `estatedb-pg`
   - Database: `estatedb`
   - User: `estatedb_user`
   - Plan: **Free**
   - Click **Create Database**.
   - Copy the **Internal Database URL** (e.g. `postgres://estatedb_user:...@dpg-...:5432/estatedb`).

2. **Create Web Service on Render**:
   - Click **New +** &rarr; **Web Service**.
   - Connect your GitHub repository.
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Environment Variables:
     - `PYTHON_VERSION`: `3.11.9`
     - `SECRET_KEY`: *(click generate or enter random string)*
     - `DATABASE_URL`: *(paste the Internal Database URL from step 1)*
   - Click **Deploy Web Service**.
   - The app will automatically initialize tables and demo data on boot!

---

## 4. Demo Logins

| Username | Password | Role | Permissions |
|---|---|---|---|
| `admin` | `Admin@123` | **Admin** | Full system access, KPI reports, users/agents/transactions management, audit log. |
| `sarah` | `Agent@123` | **Agent** | Agent desk, listing CRUD, inquiries inbox, recording deals, profile. |
| `mike` | `Agent@123` | **Agent** | Agent desk. |
| `john` | `User@123` | **Customer** | Browse, save favorites, submit inquiries, leave reviews, profile. |

---

## 5. The Database Schema

The database consists of 14 normalized tables:
- **`roles`**: System roles (`Admin`, `Agent`, `Customer`).
- **`cities`**: City and state master list.
- **`property_types`**: Residential and commercial types.
- **`amenities`**: Swimming pool, garage, gym, generator, etc.
- **`users`**: User accounts with PBKDF2 hashed passwords.
- **`agents`**: 1-to-1 extension of `users` with commission rates and agency name.
- **`properties`**: Listings with price, area, status, listing type.
- **`property_images`**: Photo URLs with primary image flag.
- **`property_amenities`**: Bridge table resolving M:N relationship.
- **`inquiries`**: Customer tour and inquiry requests.
- **`transactions`**: Closed deals (sale or rent) with commission amounts.
- **`reviews`**: Ratings and feedback for agents.
- **`favorites`**: Saved property bookmarks.
- **`audit_log`**: System change trail written automatically by triggers.

---

## 6. SQL Techniques & Architecture

- **PostgreSQL Sequences & `SERIAL`**: Primary keys utilize PostgreSQL `SERIAL` / `BIGSERIAL`.
- **PL/pgSQL Trigger Functions**: Triggers execute PL/pgSQL functions that record audit events into `audit_log` and enforce status flipping and commission calculations.
- **`ON CONFLICT` Upserts**: Review submissions utilize `ON CONFLICT (agent_id, customer_id) DO UPDATE SET ...` for clean atomic upserts.
- **`ON CONFLICT DO NOTHING`**: Favorites toggle uses `ON CONFLICT DO NOTHING` to prevent duplicate bookmark exceptions.
- **Standard ROLLUP**: Hierarchical aggregates utilize standard `GROUP BY ROLLUP (c.city_name, t.txn_type)`.
- **Date Formatting**: `TO_CHAR(ts, 'YYYY-MM')` and native PostgreSQL interval math `NOW() - (months || ' month')::interval`.
- **Live SQL Showcase**: `/database` queries `information_schema.tables`, `views`, `triggers`, and `pg_indexes` live.

---

## 7. Project Layout

```text
├─ sql/
│  ├─ 00_create_user.sql     database and user creation
│  ├─ 01_drop.sql            drop all objects (CASCADE)
│  ├─ 02_tables.sql          tables, constraints, serial PKs, indexes
│  ├─ 03_triggers.sql        PL/pgSQL audit and business logic triggers
│  ├─ 04_views.sql           v_property_listings, v_agent_performance, etc.
│  ├─ 05_procedures.sql      stored functions and procedures
│  ├─ 06_seed.sql            sample data and sequence synchronization
│  └─ run_all.sql            master script for psql
├─ app/
│  ├─ config.py              settings and DATABASE_URL resolution
│  ├─ database.py            psycopg 3 connection pool and query helpers
│  ├─ auth.py                PBKDF2 password hashing and session management
│  ├─ templating.py          Jinja2 environment, filters, error mapping
│  ├─ main.py                FastAPI application and lifespan hook
│  ├─ repositories/          data access modules (analytics, properties, etc.)
│  ├─ routers/               endpoints for public, auth, agent, admin, showcase
│  ├─ templates/             32 Jinja2 HTML templates
│  └─ static/                CSS stylesheet and sample property images
├─ scripts/
│  ├─ init_db.py             schema builder and auto-initialization utility
│  ├─ db_viewer.py           CLI table and query viewer
│  ├─ smoke_test.py          end-to-end route testing
│  ├─ check_templates.py     Jinja template linter
│  └─ check_links.py         internal hyperlink validator
├─ render.yaml               Render Blueprint for Web Service + Managed PostgreSQL
├─ requirements.txt          production dependencies (psycopg, fastapi, uvicorn)
├─ requirements-dev.txt      development extras (httpx for test client)
├─ run.py                    application launch script
└─ .env.example              sample environment file
```

---

## 8. Troubleshooting

| Symptom | Cause | Solution |
|---|---|---|
| `connection timeout expired` | PostgreSQL is not running or unreachable | Verify `DB_HOST` and `DB_PORT` in `.env` or check `DATABASE_URL`. |
| Port 5432 conflict | Another service is using port 5432 | Change `DB_PORT` in `.env` to match your PostgreSQL port. |
| `password authentication failed` | Incorrect PostgreSQL credentials | Check `DB_USER` and `DB_PASSWORD` in `.env`. |
| Web app displays offline help page | Database was unreachable on startup | Start PostgreSQL or configure `DATABASE_URL`, then restart `python run.py`. |
| Render deployment error | Missing `DATABASE_URL` | Ensure database is linked to the Web Service in Render Dashboard or via `render.yaml`. |

---

## 9. Automated Verification

All automated test suites pass cleanly:

```bash
# 1. Parse and validate all 32 templates
python scripts/check_templates.py

# 2. Validate all internal routes and links
python scripts/check_links.py

# 3. Test in-process HTTP requests across all 32 routes
python scripts/smoke_test.py
```
