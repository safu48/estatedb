"""Admin area: analytics dashboard, user/agent management, reference data,
the full deal ledger and the trigger-written audit trail.
"""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth
from ..repositories import activity, agents, analytics, lookups, properties, users
from ..templating import db_message, render

router = APIRouter(prefix="/admin")


def _admin(request: Request) -> dict:
    return auth.require_role(request, auth.ROLE_ADMIN)


@router.get("")
def dashboard(request: Request):
    """Everything the analytics module can do, on one page."""
    _admin(request)
    return render(
        request,
        "admin/dashboard.html",
        kpis=analytics.kpis(),
        monthly=analytics.monthly_sales(),
        listings_by_month=analytics.listings_added_by_month(12),
        rollup=analytics.revenue_by_city_rollup(),
        leaderboard=agents.leaderboard(limit=5),
        status_by_type=analytics.status_by_type(),
        price_bands=analytics.price_bands(),
        busy_cities=analytics.busy_cities(min_listings=2),
        priciest=analytics.priciest_per_city(),
        feed=analytics.recent_activity(limit=10),
        audit_counts=analytics.audit_counts(),
        role_counts=users.counts_by_role(),
        most_favorited=activity.most_favorited(limit=5),
    )


# ---------------------------------------------------------------------------
#  Users and agents
# ---------------------------------------------------------------------------
@router.get("/users")
def user_list(request: Request):
    _admin(request)
    role = request.query_params.get("role") or None
    return render(request, "admin/users.html",
                  rows=users.list_all(role), active_role=role,
                  role_counts=users.counts_by_role())


@router.post("/users/{user_id}/toggle")
def toggle_user(request: Request, user_id: int):
    """Activate / deactivate an account."""
    admin = _admin(request)
    if user_id == admin["user_id"]:
        return RedirectResponse(
            "/admin/users?error=You cannot deactivate your own account.",
            status_code=303)
    users.toggle_active(user_id)
    return RedirectResponse("/admin/users?notice=Account updated.",
                            status_code=303)


@router.get("/agents/new")
def new_agent_form(request: Request):
    _admin(request)
    return render(request, "admin/agent_form.html")


@router.post("/agents/new")
def create_agent(request: Request,
                 username: str = Form(...), email: str = Form(...),
                 password: str = Form(...), full_name: str = Form(...),
                 phone: str = Form(""), license_no: str = Form(...),
                 agency_name: str = Form(""),
                 commission_rate: float = Form(2.5), bio: str = Form("")):
    """Create an agent: USERS + AGENTS inserted as one transaction."""
    _admin(request)
    if users.username_taken(username.strip(), email.strip()):
        return render(request, "admin/agent_form.html",
                      error="That username or e-mail is already registered.")
    try:
        new_id = users.create_agent(username.strip(), email.strip(), password,
                                   full_name.strip(), phone.strip(),
                                   license_no.strip(), agency_name.strip(),
                                   commission_rate, bio.strip())
    except Exception as exc:  # noqa: BLE001
        return render(request, "admin/agent_form.html",
                      error=db_message(exc))
    return RedirectResponse(
        f"/agents/{new_id}?notice=Agent account created.", status_code=303)


# ---------------------------------------------------------------------------
#  Properties
# ---------------------------------------------------------------------------
@router.get("/properties")
def property_list(request: Request):
    _admin(request)
    filters = {k: v for k in ("status", "city_id", "type_id", "listing_type",
                              "keyword", "agent_id")
               if (v := request.query_params.get(k, "").strip())}
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1
    per_page = 20
    total = properties.count(filters)
    total_pages = max(1, -(-total // per_page))
    page = min(page, total_pages)

    return render(request, "admin/properties.html",
                  rows=properties.search(filters, page=page, per_page=per_page,
                                         sort="newest"),
                  total=total, page=page, total_pages=total_pages,
                  filters=filters, cities=lookups.cities(),
                  types=lookups.property_types(),
                  agent_rows=agents.list_all("name"))


@router.post("/properties/{property_id}/delete")
def delete_property(request: Request, property_id: int):
    _admin(request)
    try:
        properties.delete(property_id)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/admin/properties?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/admin/properties?notice=Listing deleted.",
                            status_code=303)


@router.post("/properties/{property_id}/featured")
def toggle_featured(request: Request, property_id: int):
    _admin(request)
    properties.toggle_featured(property_id)
    return RedirectResponse("/admin/properties?notice=Featured flag toggled.",
                            status_code=303)


# ---------------------------------------------------------------------------
#  Deals and inquiries
# ---------------------------------------------------------------------------
@router.get("/transactions")
def transaction_list(request: Request):
    _admin(request)
    return render(request, "admin/transactions.html",
                  rows=analytics.all_transactions(),
                  monthly=analytics.monthly_sales(),
                  rollup=analytics.revenue_by_city_rollup())


@router.get("/inquiries")
def inquiry_list(request: Request):
    _admin(request)
    return render(request, "admin/inquiries.html",
                  rows=activity.all_inquiries(),
                  counts=activity.inquiry_counts_by_status())


# ---------------------------------------------------------------------------
#  Reference data
# ---------------------------------------------------------------------------
@router.get("/lookups")
def lookup_admin(request: Request):
    _admin(request)
    return render(request, "admin/lookups.html",
                  cities=lookups.cities_with_counts(),
                  types=lookups.types_with_counts(),
                  amenities=lookups.amenities_with_counts(),
                  unused=lookups.unused_amenities())


@router.post("/lookups/city")
def add_city(request: Request, city_name: str = Form(...),
             state: str = Form(""), country: str = Form("USA")):
    _admin(request)
    try:
        lookups.add_city(city_name.strip(), state.strip(), country.strip())
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/admin/lookups?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/admin/lookups?notice=City added.", status_code=303)


@router.post("/lookups/city/{city_id}/delete")
def delete_city(request: Request, city_id: int):
    _admin(request)
    try:
        lookups.delete_city(city_id)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/admin/lookups?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/admin/lookups?notice=City deleted.",
                            status_code=303)


@router.post("/lookups/type")
def add_type(request: Request, type_name: str = Form(...)):
    _admin(request)
    try:
        lookups.add_property_type(type_name.strip())
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/admin/lookups?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/admin/lookups?notice=Property type added.",
                            status_code=303)


@router.post("/lookups/amenity")
def add_amenity(request: Request, amenity_name: str = Form(...)):
    _admin(request)
    try:
        lookups.add_amenity(amenity_name.strip())
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/admin/lookups?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/admin/lookups?notice=Amenity added.",
                            status_code=303)


@router.post("/lookups/amenity/{amenity_id}/delete")
def delete_amenity(request: Request, amenity_id: int):
    _admin(request)
    try:
        lookups.delete_amenity(amenity_id)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/admin/lookups?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/admin/lookups?notice=Amenity deleted.",
                            status_code=303)


# ---------------------------------------------------------------------------
#  Audit trail
# ---------------------------------------------------------------------------
@router.get("/audit")
def audit(request: Request):
    """Rows written by trg_properties_audit -- nothing here is inserted by Python."""
    _admin(request)
    action = request.query_params.get("action") or None
    return render(request, "admin/audit.html",
                  rows=analytics.audit_log(limit=100, action=action),
                  counts=analytics.audit_counts(), active_action=action)
