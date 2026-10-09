"""EstateDB -- FastAPI application entry point.

Run with:  python -m uvicorn app.main:app --reload
       or:  python run.py
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import database as db
from .auth import AuthRedirect
from .config import settings
from .routers import (admin, agent_area, auth_routes, customer, public,
                      showcase)
from .templating import render


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Open the PostgreSQL connection pool on start-up, close it on shutdown.

    A failure here is remembered rather than raised, so the site can still
    serve a page explaining how to fix the connection.
    """
    db.init_pool()
    if db.STARTUP_ERROR:
        print("\n*** PostgreSQL connection failed ***")
        print(db.STARTUP_ERROR)
        print("The site will start, but pages will show setup help.")
        print(f"Make sure PostgreSQL is running on port {settings.DB_PORT} (or DATABASE_URL is set), then restart.\n")
    else:
        print(f"Connected to PostgreSQL at {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME} "
              f"as {settings.DB_USER}")
        try:
            from scripts.init_db import auto_init_if_needed
            auto_init_if_needed()
        except Exception as exc:
            print(f"Note on auto-init: {exc}")
    yield
    db.close_pool()


app = FastAPI(title="EstateDB", lifespan=lifespan)

# Signed-cookie sessions hold the logged-in user.
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY,
                   session_cookie="estatedb_session")

app.mount("/static",
          StaticFiles(directory=Path(__file__).parent / "static"),
          name="static")

app.include_router(public.router)
app.include_router(auth_routes.router)
app.include_router(customer.router)
app.include_router(agent_area.router)
app.include_router(admin.router)
app.include_router(showcase.router)


@app.middleware("http")
async def database_guard(request: Request, call_next):
    """Short-circuit every page with setup help while the database is down.

    Without this, a misconfigured .env produces a stack trace on every route;
    this way the first thing you see is what to fix.
    """
    path = request.url.path
    if db.STARTUP_ERROR and not path.startswith("/static"):
        return render(request, "db_error.html",
                      message=db.STARTUP_ERROR, settings=settings,
                      client_mode=db.CLIENT_MODE,
                      client_warning=db.CLIENT_WARNING)
    return await call_next(request)


@app.exception_handler(AuthRedirect)
async def auth_redirect_handler(request: Request, exc: AuthRedirect):
    """Send unauthenticated / unauthorised visitors somewhere useful."""
    return RedirectResponse(exc.location, status_code=303)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    return render(request, "error.html", message=str(exc))
