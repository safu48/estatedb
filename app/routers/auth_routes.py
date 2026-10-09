"""Login, registration and logout."""
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from .. import auth
from ..repositories import users
from ..templating import db_message, render

router = APIRouter()

# Where each role lands after logging in.
HOME_FOR_ROLE = {
    auth.ROLE_ADMIN: "/admin",
    auth.ROLE_AGENT: "/agent",
    auth.ROLE_CUSTOMER: "/me",
}


@router.get("/login")
def login_form(request: Request):
    if auth.current_user(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "login.html",
                  next_url=request.query_params.get("next", ""))


@router.post("/login")
def do_login(request: Request, username: str = Form(...),
             password: str = Form(...), next_url: str = Form("")):
    """Verify the password against the PBKDF2 hash stored in USERS."""
    row = users.get_by_username(username.strip())

    if not row or not auth.verify_password(password, row["password_hash"],
                                           row["password_salt"]):
        return render(request, "login.html",
                      error="Incorrect username or password.",
                      next_url=next_url)

    if row["is_active"] != "Y":
        return render(request, "login.html",
                      error="This account has been deactivated.",
                      next_url=next_url)

    auth.login_user(request, {
        "user_id": int(row["user_id"]),
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role_name"],
        "agent_id": int(row["agent_id"]) if row["agent_id"] is not None else None,
    })

    target = next_url or HOME_FOR_ROLE.get(row["role_name"], "/")
    return RedirectResponse(target, status_code=303)


@router.get("/register")
def register_form(request: Request):
    if auth.current_user(request):
        return RedirectResponse("/", status_code=303)
    return render(request, "register.html")


@router.post("/register")
def do_register(request: Request,
                username: str = Form(...),
                email: str = Form(...),
                password: str = Form(...),
                confirm_password: str = Form(...),
                full_name: str = Form(...),
                phone: str = Form("")):
    """Create a customer account.

    The UNIQUE constraints on USERS.username / USERS.email are the real
    guarantee here; the pre-check just produces a nicer message.
    """
    form = {"username": username, "email": email, "full_name": full_name,
            "phone": phone}

    if password != confirm_password:
        return render(request, "register.html",
                      error="The two passwords do not match.", form=form)
    if len(password) < 6:
        return render(request, "register.html",
                      error="Please use a password of at least 6 characters.",
                      form=form)
    if users.username_taken(username.strip(), email.strip()):
        return render(request, "register.html",
                      error="That username or e-mail is already registered.",
                      form=form)

    try:
        user_id = users.create_customer(username.strip(), email.strip(),
                                       password, full_name.strip(), phone.strip())
    except Exception as exc:  # noqa: BLE001
        return render(request, "register.html",
                      error=db_message(exc), form=form)

    auth.login_user(request, {
        "user_id": user_id,
        "username": username.strip(),
        "full_name": full_name.strip(),
        "role": auth.ROLE_CUSTOMER,
        "agent_id": None,
    })
    return RedirectResponse("/me?notice=Welcome to EstateDB.", status_code=303)


@router.get("/logout")
def logout(request: Request):
    auth.logout_user(request)
    return RedirectResponse("/?notice=You have been signed out.", status_code=303)
