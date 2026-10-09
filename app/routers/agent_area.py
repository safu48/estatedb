"""Agent area: manage listings, work the inquiry inbox, record sales."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth
from ..repositories import activity, agents, analytics, lookups, properties
from ..templating import db_message, render

router = APIRouter(prefix="/agent")


def _agent_id(request: Request) -> int:
    """The signed-in agent's id (also their user_id)."""
    user = auth.require_role(request, auth.ROLE_AGENT)
    return int(user["agent_id"] or user["user_id"])


def _owns(agent_id: int, property_id: int) -> bool:
    """Agents may only touch their own listings."""
    return properties.owner_agent_id(property_id) == agent_id


@router.get("")
def dashboard(request: Request):
    """Performance summary straight from v_agent_performance."""
    aid = _agent_id(request)
    return render(
        request,
        "agent/dashboard.html",
        me=agents.get(aid),
        listings=properties.by_agent(aid),
        inquiry_counts=activity.inquiry_counts_by_status(aid),
        inquiries=activity.inquiries_for_agent(aid)[:5],
        transactions=analytics.transactions_for_agent(aid),
        reviews=agents.reviews_for(aid)[:5],
    )


# ---------------------------------------------------------------------------
#  Listings
# ---------------------------------------------------------------------------
@router.get("/properties")
def my_properties(request: Request):
    aid = _agent_id(request)
    return render(request, "agent/properties.html",
                  rows=properties.by_agent(aid))


@router.get("/properties/new")
def new_property_form(request: Request):
    _agent_id(request)
    return render(request, "agent/property_form.html", p=None,
                  cities=lookups.cities(), types=lookups.property_types(),
                  all_amenities=lookups.amenities(), selected_amenities=set(),
                  images=[])


@router.post("/properties/new")
async def create_property(request: Request):
    """Insert a listing plus its images and amenities in one transaction."""
    aid = _agent_id(request)
    form = await request.form()

    data = {
        "title": (form.get("title") or "").strip(),
        "description": (form.get("description") or "").strip(),
        "type_id": int(form.get("type_id")),
        "city_id": int(form.get("city_id")),
        "agent_id": aid,
        "address": (form.get("address") or "").strip(),
        "price": float(form.get("price")),
        "bedrooms": int(form.get("bedrooms") or 0),
        "bathrooms": int(form.get("bathrooms") or 0),
        "area_sqft": float(form.get("area_sqft") or 0) or None,
        "year_built": int(form.get("year_built")) if form.get("year_built") else None,
        "listing_type": form.get("listing_type"),
        "status": form.get("status") or "AVAILABLE",
        "featured": "Y" if form.get("featured") else "N",
    }
    image_urls = [u for u in form.getlist("image_url") if u.strip()]
    if not image_urls:
        image_urls = ["/static/img/prop-01.jpg"]
    amenity_ids = [int(a) for a in form.getlist("amenity_id")]

    try:
        new_id = properties.create(data, image_urls, amenity_ids)
    except Exception as exc:  # noqa: BLE001
        return render(request, "agent/property_form.html", p=None,
                      cities=lookups.cities(), types=lookups.property_types(),
                      all_amenities=lookups.amenities(),
                      selected_amenities=set(amenity_ids), images=[],
                      error=db_message(exc), form=dict(form))

    return RedirectResponse(
        f"/property/{new_id}?notice=Listing created (id {new_id}).",
        status_code=303)


@router.get("/properties/{property_id}/edit")
def edit_property_form(request: Request, property_id: int):
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)

    row = properties.get(property_id)
    if not row:
        return RedirectResponse("/agent/properties?error=Listing not found.",
                                status_code=303)

    return render(request, "agent/property_form.html", p=row,
                  cities=lookups.cities(), types=lookups.property_types(),
                  all_amenities=lookups.amenities(),
                  selected_amenities={int(a["amenity_id"])
                                      for a in properties.amenities(property_id)},
                  images=properties.images(property_id))


@router.post("/properties/{property_id}/edit")
async def save_property(request: Request, property_id: int):
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)

    form = await request.form()
    data = {
        "title": (form.get("title") or "").strip(),
        "description": (form.get("description") or "").strip(),
        "type_id": int(form.get("type_id")),
        "city_id": int(form.get("city_id")),
        "address": (form.get("address") or "").strip(),
        "price": float(form.get("price")),
        "bedrooms": int(form.get("bedrooms") or 0),
        "bathrooms": int(form.get("bathrooms") or 0),
        "area_sqft": float(form.get("area_sqft") or 0) or None,
        "year_built": int(form.get("year_built")) if form.get("year_built") else None,
        "listing_type": form.get("listing_type"),
        "status": form.get("status") or "AVAILABLE",
        "featured": "Y" if form.get("featured") else "N",
    }
    amenity_ids = [int(a) for a in form.getlist("amenity_id")]

    try:
        properties.update(property_id, data, amenity_ids)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"/agent/properties/{property_id}/edit?error={db_message(exc)}",
            status_code=303)

    return RedirectResponse(
        f"/property/{property_id}?notice=Listing updated.", status_code=303)


@router.post("/properties/{property_id}/status")
def change_status(request: Request, property_id: int, status: str = Form(...)):
    """Update availability -- logged automatically by trg_properties_audit."""
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)
    try:
        properties.set_status(property_id, status)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agent/properties?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse(f"/agent/properties?notice=Status set to {status}.",
                            status_code=303)


@router.post("/properties/{property_id}/featured")
def toggle_featured(request: Request, property_id: int):
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)
    properties.toggle_featured(property_id)
    return RedirectResponse("/agent/properties?notice=Featured flag toggled.",
                            status_code=303)


@router.post("/properties/{property_id}/delete")
def delete_property(request: Request, property_id: int):
    """Delete a listing.

    A property with a recorded transaction cannot be deleted -- the FK on
    TRANSACTIONS has no cascade, so MySQL raises Error 1451 and we explain it.
    """
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)
    try:
        properties.delete(property_id)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agent/properties?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/agent/properties?notice=Listing deleted.",
                            status_code=303)


@router.post("/properties/{property_id}/images")
def add_image(request: Request, property_id: int, image_url: str = Form(...),
              is_primary: str = Form("")):
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)
    properties.add_image(property_id, image_url.strip(), bool(is_primary))
    return RedirectResponse(
        f"/agent/properties/{property_id}/edit?notice=Image added.",
        status_code=303)


@router.post("/properties/{property_id}/images/{image_id}/delete")
def remove_image(request: Request, property_id: int, image_id: int):
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/properties?error=That listing is not yours.",
                                status_code=303)
    properties.delete_image(image_id)
    return RedirectResponse(
        f"/agent/properties/{property_id}/edit?notice=Image removed.",
        status_code=303)


# ---------------------------------------------------------------------------
#  Inquiry inbox
# ---------------------------------------------------------------------------
@router.get("/inquiries")
def inbox(request: Request):
    aid = _agent_id(request)
    status = request.query_params.get("status") or None
    return render(request, "agent/inquiries.html",
                  rows=activity.inquiries_for_agent(aid, status),
                  counts=activity.inquiry_counts_by_status(aid),
                  active_status=status)


@router.post("/inquiries/{inquiry_id}/status")
def set_inquiry_status(request: Request, inquiry_id: int,
                       status: str = Form(...)):
    """Advance an inquiry through the SP_UPDATE_INQUIRY_STATUS procedure."""
    aid = _agent_id(request)
    if activity.inquiry_owner_agent(inquiry_id) != aid:
        return RedirectResponse("/agent/inquiries?error=That inquiry is not yours.",
                                status_code=303)
    try:
        activity.set_inquiry_status(inquiry_id, status)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agent/inquiries?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse(f"/agent/inquiries?notice=Marked {status}.",
                            status_code=303)


# ---------------------------------------------------------------------------
#  Deals
# ---------------------------------------------------------------------------
@router.get("/sales")
def sales(request: Request):
    """Deal history plus the form that calls SP_RECORD_SALE."""
    aid = _agent_id(request)
    open_listings = [r for r in properties.by_agent(aid)
                     if r["status"] in ("AVAILABLE", "PENDING")]
    return render(request, "agent/sales.html",
                  rows=analytics.transactions_for_agent(aid),
                  open_listings=open_listings,
                  buyers=analytics.buyers_for_dropdown(),
                  me=agents.get(aid))


@router.post("/sales")
def record_sale(request: Request, property_id: int = Form(...),
                buyer_id: int = Form(...), sale_price: float = Form(...),
                txn_type: str = Form(...)):
    """Close a deal.

    All validation lives in the PL/SQL package: it refuses a property that is
    already sold (ORA-20001), a non-positive price (ORA-20002), a bad type
    (ORA-20003) or a missing property (ORA-20004).
    """
    aid = _agent_id(request)
    if not _owns(aid, property_id):
        return RedirectResponse("/agent/sales?error=That listing is not yours.",
                                status_code=303)
    try:
        txn_id = analytics.record_sale(property_id, buyer_id, sale_price, txn_type)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agent/sales?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse(
        f"/agent/sales?notice=Deal recorded (transaction {txn_id}). "
        f"Commission and property status were set by triggers.",
        status_code=303)


# ---------------------------------------------------------------------------
#  Agent profile
# ---------------------------------------------------------------------------
@router.get("/profile")
def profile_form(request: Request):
    aid = _agent_id(request)
    return render(request, "agent/profile.html", me=agents.get(aid))


@router.post("/profile")
def save_profile(request: Request, agency_name: str = Form(""),
                 license_no: str = Form(...),
                 commission_rate: float = Form(...), bio: str = Form("")):
    aid = _agent_id(request)
    try:
        agents.update_profile(aid, agency_name.strip(), license_no.strip(),
                              commission_rate, bio.strip())
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/agent/profile?error={db_message(exc)}",
                                status_code=303)
    return RedirectResponse("/agent/profile?notice=Profile saved.",
                            status_code=303)
