"""Public pages: home, listings search, property detail, agent directory."""
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth
from ..repositories import activity, agents, analytics, lookups, properties
from ..templating import db_message, render

router = APIRouter()

PER_PAGE = 9

# Filter keys read from the query string and handed to the repository.
FILTER_KEYS = (
    "keyword", "city_id", "type_id", "listing_type", "status", "min_price",
    "max_price", "bedrooms", "bathrooms", "min_area", "amenity_id", "featured",
    "agent_id",
)


def _collect_filters(request: Request) -> dict:
    """Pull the filter values out of the query string, dropping blanks."""
    return {
        key: value
        for key in FILTER_KEYS
        if (value := request.query_params.get(key, "").strip())
    }


def _query_string(filters: dict, sort: str, page: Optional[int] = None) -> str:
    """Rebuild the query string so pager links keep the current filters."""
    parts = [f"{k}={v}" for k, v in filters.items()]
    if sort:
        parts.append(f"sort={sort}")
    if page:
        parts.append(f"page={page}")
    return "&".join(parts)


@router.get("/")
def home(request: Request):
    """Landing page: featured listings, market snapshot, top agents."""
    user = auth.current_user(request)
    return render(
        request,
        "home.html",
        featured=properties.featured(limit=6),
        newest=properties.newest(limit=3),
        city_stats=lookups.cities_with_counts()[:6],
        kpis=analytics.kpis(),
        top_agents=agents.leaderboard(limit=3),
        cities=lookups.cities(),
        types=lookups.property_types(),
        favorite_ids=activity.favorite_ids(user["user_id"]) if user else set(),
    )


@router.get("/listings")
def listings(request: Request):
    """Search results with filters, sorting and ROWNUM-based pagination."""
    user = auth.current_user(request)
    filters = _collect_filters(request)
    sort = request.query_params.get("sort", properties.DEFAULT_SORT)
    try:
        page = max(1, int(request.query_params.get("page", 1)))
    except ValueError:
        page = 1

    total = properties.count(filters)
    total_pages = max(1, -(-total // PER_PAGE))  # ceiling division
    page = min(page, total_pages)
    rows = properties.search(filters, page=page, per_page=PER_PAGE, sort=sort)

    return render(
        request,
        "listings.html",
        rows=rows,
        total=total,
        page=page,
        total_pages=total_pages,
        per_page=PER_PAGE,
        filters=filters,
        sort=sort,
        sort_options=properties.SORT_OPTIONS,
        base_query=_query_string(filters, sort),
        cities=lookups.cities(),
        types=lookups.property_types(),
        amenities=lookups.amenities(),
        price_range=lookups.price_range(),
        favorite_ids=activity.favorite_ids(user["user_id"]) if user else set(),
    )


@router.get("/property/{property_id}")
def property_detail(request: Request, property_id: int):
    """One listing: gallery, amenities, agent card, similar homes."""
    row = properties.get(property_id)
    if not row:
        return render(request, "error.html",
                      message=f"Property {property_id} was not found.")

    user = auth.current_user(request)
    return render(
        request,
        "property_detail.html",
        p=row,
        images=properties.images(property_id),
        amenities=properties.amenities(property_id),
        similar=properties.similar(property_id, limit=3),
        is_favorite=(activity.is_favorite(user["user_id"], property_id)
                     if user else False),
    )


@router.post("/property/{property_id}/inquire")
def create_inquiry(request: Request, property_id: int,
                   message: str = Form(...),
                   preferred_date: str = Form("")):
    """Send a viewing request (customers only)."""
    user = auth.require_login(request)
    if user["role"] != auth.ROLE_CUSTOMER:
        return RedirectResponse(
            f"/property/{property_id}?error=Only customer accounts can send inquiries.",
            status_code=303,
        )
    try:
        activity.create_inquiry(property_id, user["user_id"], message,
                                preferred_date or None)
        notice = "Your inquiry has been sent to the agent."
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"/property/{property_id}?error={db_message(exc)}", status_code=303
        )
    return RedirectResponse(f"/property/{property_id}?notice={notice}",
                            status_code=303)


@router.post("/property/{property_id}/favorite")
def toggle_favorite(request: Request, property_id: int,
                    redirect_to: str = Form("")):
    """Save or unsave a listing."""
    user = auth.require_login(request)
    saved = activity.toggle_favorite(user["user_id"], property_id)
    target = redirect_to or f"/property/{property_id}"
    joiner = "&" if "?" in target else "?"
    notice = "Saved to your favourites." if saved else "Removed from favourites."
    return RedirectResponse(f"{target}{joiner}notice={notice}", status_code=303)


@router.get("/agents")
def agent_directory(request: Request):
    """All agents, ranked by the metric chosen in the drop-down."""
    sort = request.query_params.get("sort", "sales")
    return render(request, "agents.html",
                  rows=agents.list_all(sort=sort), sort=sort)


@router.get("/agents/{agent_id}")
def agent_profile(request: Request, agent_id: int):
    """One agent: KPIs from the view, their listings and their reviews."""
    row = agents.get(agent_id)
    if not row:
        return render(request, "error.html",
                      message=f"Agent {agent_id} was not found.")

    user = auth.current_user(request)
    my_review = None
    if user and user["role"] == auth.ROLE_CUSTOMER:
        my_review = agents.review_by(agent_id, user["user_id"])

    return render(
        request,
        "agent_profile.html",
        a=row,
        listings=properties.by_agent(agent_id),
        reviews=agents.reviews_for(agent_id),
        distribution=agents.rating_distribution(agent_id),
        my_review=my_review,
    )


@router.post("/agents/{agent_id}/review")
def submit_review(request: Request, agent_id: int,
                  rating: int = Form(...), comments: str = Form("")):
    """Leave or update a review (MERGE upsert in the repository)."""
    user = auth.require_role(request, auth.ROLE_CUSTOMER)
    try:
        agents.upsert_review(agent_id, user["user_id"], int(rating), comments)
        notice = "Thanks -- your review has been saved."
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agents/{agent_id}?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse(f"/agents/{agent_id}?notice={notice}", status_code=303)


@router.get("/market")
def market_overview(request: Request):
    """Public market statistics page (aggregates, crosstabs, price bands)."""
    return render(
        request,
        "market.html",
        city_stats=lookups.cities_with_counts(),
        type_stats=lookups.types_with_counts(),
        price_bands=analytics.price_bands(),
        status_by_type=analytics.status_by_type(),
        priciest=analytics.priciest_per_city(),
        busy_cities=analytics.busy_cities(min_listings=2),
        popular_amenities=lookups.amenities_with_counts(),
        most_favorited=activity.most_favorited(limit=5),
    )
