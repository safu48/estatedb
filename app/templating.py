"""Shared Jinja2 environment: template lookup, custom filters and a render()
helper that injects the logged-in user into every page.
"""
from datetime import date, datetime
from pathlib import Path
import re
from typing import Any, Optional

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ---------------------------------------------------------------------------
#  Filters
# ---------------------------------------------------------------------------
def money(value: Any, decimals: int = 0) -> str:
    """1234567 -> "৳1,234,567" (blank for NULL)."""
    if value is None:
        return "--"
    try:
        return f"৳{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return str(value)


def money_short(value: Any) -> str:
    """Compact currency for tight spaces: 1250000 -> "৳1.25M"."""
    if value is None:
        return "--"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if v >= 1_000_000:
        return f"৳{v / 1_000_000:.2f}M".replace(".00M", "M")
    if v >= 1_000:
        return f"৳{v / 1_000:.0f}K"
    return f"৳{v:,.0f}"


def num(value: Any) -> str:
    """Thousands separators for plain numbers."""
    if value is None:
        return "--"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{int(f):,}" if f == int(f) else f"{f:,.2f}"


def datefmt(value: Any, fmt: str = "%d %b %Y") -> str:
    if value is None:
        return "--"
    if isinstance(value, (datetime, date)):
        return value.strftime(fmt)
    return str(value)


def date_input(value: Any) -> str:
    """Format a date for an <input type="date"> value attribute."""
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return ""


def stars(rating: Any) -> str:
    """4 -> filled/empty star glyphs for the review widgets."""
    if rating is None:
        return "No reviews"
    try:
        r = int(round(float(rating)))
    except (TypeError, ValueError):
        return "No reviews"
    r = max(0, min(5, r))
    return "★" * r + "☆" * (5 - r)


def truncate_words(value: Any, count: int = 24) -> str:
    if not value:
        return ""
    words = str(value).split()
    if len(words) <= count:
        return " ".join(words)
    return " ".join(words[:count]) + "..."


def status_class(status: Any) -> str:
    """Map a status value to its CSS badge modifier."""
    return {
        "AVAILABLE": "badge-available",
        "PENDING": "badge-pending",
        "SOLD": "badge-sold",
        "RENTED": "badge-rented",
        "NEW": "badge-new",
        "CONTACTED": "badge-contacted",
        "SCHEDULED": "badge-scheduled",
        "CLOSED": "badge-closed",
        "SALE": "badge-sale",
        "RENT": "badge-rent",
        "INSERT": "badge-insert",
        "UPDATE": "badge-update",
        "DELETE": "badge-delete",
        "ADMIN": "badge-admin",
        "AGENT": "badge-agent",
        "CUSTOMER": "badge-customer",
    }.get(str(status).upper(), "")


def status_label(status: Any) -> str:
    """Map a database status keyword to a clean, easily readable English label."""
    s = str(status).upper() if status else ""
    return {
        "AVAILABLE": "Available",
        "PENDING": "Pending",
        "SOLD": "Sold",
        "RENTED": "Rented",
        "NEW": "New",
        "CONTACTED": "Contacted",
        "SCHEDULED": "Scheduled",
        "CLOSED": "Closed",
        "SALE": "For Sale",
        "RENT": "For Rent",
        "INSERT": "INSERT",
        "UPDATE": "UPDATE",
        "DELETE": "DELETE",
        "ADMIN": "Admin",
        "AGENT": "Agent",
        "CUSTOMER": "Customer",
    }.get(s, str(status) if status is not None else "")


templates.env.filters["money"] = money
templates.env.filters["money_short"] = money_short
templates.env.filters["num"] = num
templates.env.filters["datefmt"] = datefmt
templates.env.filters["date_input"] = date_input
templates.env.filters["stars"] = stars
templates.env.filters["truncate_words"] = truncate_words
templates.env.filters["status_class"] = status_class
templates.env.filters["status_label"] = status_label


# ---------------------------------------------------------------------------
#  Render helper
# ---------------------------------------------------------------------------
def render(request: Request, template_name: str, **context: Any):
    """Render a template with the common context already filled in."""
    session = request.scope.get("session") or {}
    base = {
        "request": request,
        "user": session.get("user"),
        "notice": request.query_params.get("notice"),
        "error": request.query_params.get("error"),
        "current_path": request.url.path,
    }
    base.update(context)
    return templates.TemplateResponse(request, template_name, base)


def db_message(exc: Exception) -> str:
    """Turn a database error into something a user can read in Bangla.

    Handles PostgreSQL & MySQL error codes and messages:
      - Unique constraint violation / duplicate key
      - Foreign key constraint violation (delete / insert)
      - Not null constraint violation
      - Check constraint violation
      - User-defined RAISE EXCEPTION / SIGNAL from stored procedures
    """
    text = str(exc)
    low = text.lower()
    if "1062" in text or "duplicate key" in low or "unique constraint" in low or "duplicate entry" in low:
        return "এই তথ্যটি ইতিমধ্যে ডেটাবেসে সংরক্ষিত রয়েছে (ইউনিক কনস্ট্রেইন্ট)।"
    if "1451" in text or ("foreign key constraint" in low and ("update or delete" in low or "delete" in low)):
        return "অন্যান্য টেবিলের সাথে সম্পর্ক বিদ্যমান থাকায় এই রেকর্ডটি মুছে ফেলা সম্ভব নয়।"
    if "1452" in text or ("foreign key constraint" in low and ("insert or update" in low or "is not present in table" in low)):
        return "সম্পর্কিত কোনো রেকর্ড খুঁজে পাওয়া যায়নি (ফরেন কি কনস্ট্রেইন্ট)।"
    if "3819" in text or "4025" in text or "check constraint" in low:
        return "প্রদত্ত মানটি অনুমোদিত সীমার বাইরে (চেক কনস্ট্রেইন্ট)।"
    if "1048" in text or "cannot be null" in low or "not-null constraint" in low:
        return "প্রয়োজনীয় ঘরটি পূরণ করা হয়নি (NOT NULL কনস্ট্রেইন্ট)।"

    # User-defined RAISE EXCEPTION / SIGNAL messages
    if "property does not exist" in low:
        return "প্রপার্টিটি খুঁজে পাওয়া যায়নি।"
    if "already closed" in low:
        return "প্রপার্টিটি ইতিমধ্যে বিক্রয় বা ভাড়া হয়ে গেছে।"
    if "must be positive" in low:
        return "মূল্য অবশ্যই ধনাত্মক সংখ্যা হতে হবে।"
    if "inquiry not found" in low:
        return "অনুসন্ধানটি খুঁজে পাওয়া যায়নি।"
    if "invalid inquiry status" in low:
        return "অনুসন্ধানের স্ট্যাটাসটি সঠিক নয়।"

    match = re.search(r"\(\s*1644\s*,\s*['\"]([^'\"]+)['\"]\s*\)", text)
    if match:
        return match.group(1)

    return text.splitlines()[0] if text else "ডেটাবেস ত্রুটি।"
