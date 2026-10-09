"""Customer area: saved properties, inquiries, reviews and profile."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth
from ..repositories import activity, agents, users
from ..templating import db_message, render

router = APIRouter(prefix="/me")


@router.get("")
def dashboard(request: Request):
    """Overview: saved homes, open inquiries and personalised suggestions."""
    user = auth.require_login(request)
    uid = user["user_id"]
    return render(
        request,
        "customer/dashboard.html",
        favorites=activity.favorites_for(uid),
        inquiries=activity.inquiries_by_customer(uid),
        recommendations=activity.recommendations(uid, limit=3),
        reviews=agents.reviews_by_customer(uid),
        profile=users.get_by_id(uid),
    )


@router.get("/favorites")
def favorites(request: Request):
    user = auth.require_login(request)
    rows = activity.favorites_for(user["user_id"])
    return render(request, "customer/favorites.html", rows=rows,
                  favorite_ids={int(r["property_id"]) for r in rows})


@router.get("/inquiries")
def inquiries(request: Request):
    user = auth.require_login(request)
    return render(request, "customer/inquiries.html",
                  rows=activity.inquiries_by_customer(user["user_id"]))


@router.get("/reviews")
def reviews(request: Request):
    user = auth.require_login(request)
    return render(request, "customer/reviews.html",
                  rows=agents.reviews_by_customer(user["user_id"]))


@router.post("/reviews/{review_id}/delete")
def delete_review(request: Request, review_id: int):
    """Delete one of my own reviews (the DELETE is scoped to customer_id)."""
    user = auth.require_login(request)
    removed = agents.delete_review(review_id, user["user_id"])
    notice = "Review deleted." if removed else "That review was not found."
    return RedirectResponse(f"/me/reviews?notice={notice}", status_code=303)


@router.get("/profile")
def profile_form(request: Request):
    user = auth.require_login(request)
    return render(request, "customer/profile.html",
                  profile=users.get_by_id(user["user_id"]))


@router.post("/profile")
def save_profile(request: Request, full_name: str = Form(...),
                 email: str = Form(...), phone: str = Form("")):
    user = auth.require_login(request)
    try:
        users.update_profile(user["user_id"], full_name.strip(), phone.strip(),
                             email.strip())
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"/me/profile?error={db_message(exc)}",
                                status_code=303)

    # Keep the name in the session in step with the database.
    session_user = dict(user)
    session_user["full_name"] = full_name.strip()
    auth.login_user(request, session_user)
    return RedirectResponse("/me/profile?notice=Profile updated.", status_code=303)


@router.post("/password")
def change_password(request: Request, current_password: str = Form(...),
                    new_password: str = Form(...),
                    confirm_password: str = Form(...)):
    """Change my password, re-verifying the current one first."""
    user = auth.require_login(request)
    row = users.get_by_username(user["username"])

    if not row or not auth.verify_password(current_password,
                                           row["password_hash"],
                                           row["password_salt"]):
        return RedirectResponse(
            "/me/profile?error=Your current password was incorrect.",
            status_code=303)
    if new_password != confirm_password:
        return RedirectResponse(
            "/me/profile?error=The new passwords do not match.", status_code=303)
    if len(new_password) < 6:
        return RedirectResponse(
            "/me/profile?error=Please use at least 6 characters.", status_code=303)

    users.change_password(user["user_id"], new_password)
    return RedirectResponse("/me/profile?notice=Password changed.", status_code=303)
