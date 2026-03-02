"""Admin panel — cookie-based session authentication.

How it works
------------
Every request to an admin page calls ``has_page_permission()``.  That method
reads a Starlette session cookie and validates it:

  1. No valid cookie → 307 redirect to ``/admin/login?redirect=<path>``
  2. Valid cookie but inactive > 20 min → cookie cleared, same redirect
  3. Valid, active session → update ``last_activity`` (sliding window) and
     allow the request through

The session cookie is an ``itsdangerous`` TimestampSigner payload stored
client-side — no extra database table is needed.  The cookie's ``Max-Age``
matches the inactivity timeout, so the browser also expires it automatically.

Login flow
----------
  GET  /admin/login  — render the HTML login form
  POST /admin/login  — validate credentials (bcrypt) and role == admin,
                       then set session and redirect to the original page

Logout flow
-----------
  GET  /admin/logout — clear the session cookie, redirect to /admin/login

Security properties
-------------------
  • HttpOnly cookie (Starlette SessionMiddleware default)
  • SameSite=Lax  (CSRF mitigation for cross-site navigations)
  • Session fixation prevention (``session.clear()`` before writing new data)
  • Open-redirect prevention (``_safe_redirect`` restricts to /admin/*)
  • Non-admin and inactive users are rejected at ``_authenticate_admin``
  • Set ``https_only=True`` in ``mount_app`` for HTTPS deployments
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_amis_admin.admin.site import AdminSite
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.enums import UserRole
from app.core.security import verify_password
from app.db.session import AsyncSessionFactory
from app.models.user import User

# ── Session config ────────────────────────────────────────────────────────────

_SESSION_UID  = "admin_uid"   # key: user UUID string
_SESSION_LAST = "admin_last"  # key: last-activity UNIX timestamp (float)
_TIMEOUT      = 20 * 60       # 20 minutes in seconds


# ── Internal helpers ──────────────────────────────────────────────────────────

def _is_authenticated(request: Request) -> bool:
    """Return True when the session is valid; slide the 20-min inactivity window."""
    uid  = request.session.get(_SESSION_UID)
    last = request.session.get(_SESSION_LAST)
    if not uid or last is None:
        return False
    now = datetime.now(timezone.utc).timestamp()
    if now - last > _TIMEOUT:
        request.session.clear()
        return False
    request.session[_SESSION_LAST] = now  # slide the window on every request
    return True


async def _authenticate_admin(email: str, password: str) -> Optional[User]:
    """Return the User iff credentials are valid and the account is an admin.

    The DB session is closed *before* the bcrypt comparison so the connection
    is returned to the pool during the CPU-intensive hash verification.
    """
    async with AsyncSessionFactory() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

    if user is None or not user.is_active or user.role != UserRole.admin:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def _login_html(*, error: str = "", redirect: str = "") -> str:
    """Return a self-contained login page as an HTML string."""
    e   = _html.escape(error)
    rdr = _html.escape(redirect)
    err_block = f'<p class="error">{e}</p>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Pantry Mate — Admin Login</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #f0f2f5;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
    }}
    .card {{
      background: #fff;
      border-radius: 8px;
      box-shadow: 0 2px 16px rgba(0,0,0,.10);
      padding: 40px 36px 32px;
      width: 100%;
      max-width: 380px;
    }}
    h1 {{ font-size: 22px; font-weight: 700; color: #1677ff; margin-bottom: 4px; }}
    .sub {{ font-size: 13px; color: #8c8c8c; margin-bottom: 28px; }}
    label {{
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #595959;
      margin-bottom: 5px;
    }}
    input[type=email], input[type=password] {{
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #d9d9d9;
      border-radius: 6px;
      font-size: 14px;
      margin-bottom: 18px;
      outline: none;
      transition: border-color .15s;
    }}
    input:focus {{
      border-color: #1677ff;
      box-shadow: 0 0 0 2px rgba(22,119,255,.10);
    }}
    button {{
      width: 100%;
      padding: 10px;
      background: #1677ff;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: background .15s;
    }}
    button:hover {{ background: #0958d9; }}
    .error {{
      background: #fff2f0;
      border: 1px solid #ffccc7;
      border-radius: 6px;
      color: #cf1322;
      font-size: 13px;
      padding: 10px 12px;
      margin-bottom: 18px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Pantry Mate</h1>
    <p class="sub">Admin panel — sign in to continue</p>
    {err_block}
    <form method="POST" action="">
      <input type="hidden" name="redirect" value="{rdr}" />
      <label for="email">Email address</label>
      <input id="email" type="email" name="email"
             placeholder="admin@example.com"
             required autofocus autocomplete="username" />
      <label for="password">Password</label>
      <input id="password" type="password" name="password"
             required autocomplete="current-password" />
      <button type="submit">Sign in</button>
    </form>
  </div>
</body>
</html>"""


# ── AuthAdminSite ─────────────────────────────────────────────────────────────

class AuthAdminSite(AdminSite):
    """AdminSite subclass that enforces cookie-based session authentication.

    Only users whose ``role == admin`` and ``is_active == True`` may log in.
    Sessions expire after 20 minutes of inactivity (sliding window).
    No changes to ``app/main.py`` are required — authentication is fully
    self-contained within this class and mounted on the admin sub-app.
    """

    # ── Middleware ─────────────────────────────────────────────────────────────

    def mount_app(
        self,
        fastapi,
        *,
        name: str = "admin",
        enable_exception_handlers: bool = True,
        enable_db_middleware: bool = True,
    ) -> None:
        # Attach SessionMiddleware to the admin sub-app *before* mounting so
        # it wraps the entire admin ASGI stack.
        # NOTE: set https_only=True when running behind HTTPS.
        self.fastapi.add_middleware(
            SessionMiddleware,
            secret_key=settings.ADMIN_SECRET_KEY,
            session_cookie="pm_admin_session",
            max_age=_TIMEOUT,    # cookie Max-Age = inactivity timeout
            same_site="lax",     # CSRF mitigation; works with normal navigation
            https_only=False,    # ← set True in HTTPS deployments
        )
        super().mount_app(
            fastapi,
            name=name,
            enable_exception_handlers=enable_exception_handlers,
            enable_db_middleware=enable_db_middleware,
        )

    # ── Router registration ────────────────────────────────────────────────────

    def register_router(self):
        super().register_router()

        # The framework's error_no_page_permission() builds the redirect URL as:
        #   f"{site.router_path}{site.router.url_path_for('login')}?redirect=…"
        # The routes below must be named "login" / "logout" for url_path_for to
        # resolve them.  They are added directly to the admin sub-app so they
        # sit at /admin/login and /admin/logout respectively.
        self.fastapi.add_api_route(
            "/login",
            self._route_login_get,
            methods=["GET"],
            name="login",
            response_class=HTMLResponse,
            include_in_schema=False,
        )
        self.fastapi.add_api_route(
            "/login",
            self._route_login_post,
            methods=["POST"],
            include_in_schema=False,
        )
        self.fastapi.add_api_route(
            "/logout",
            self._route_logout,
            methods=["GET"],
            name="logout",
            include_in_schema=False,
        )
        return self

    # ── Permission gate ────────────────────────────────────────────────────────

    async def has_page_permission(
        self, request: Request, obj=None, action: str = None
    ) -> bool:
        """Gate every admin page behind a valid session.

        All child admins delegate here via the default PageSchemaAdmin
        implementation:
            return self.app is self or await self.app.has_page_permission(…)
        Because AdminSite is its own ``app``, overriding this method here is
        the single chokepoint that covers every registered admin view.
        """
        return _is_authenticated(request)

    # ── Route handlers ─────────────────────────────────────────────────────────

    async def _route_login_get(self, request: Request) -> HTMLResponse:
        redirect = request.query_params.get("redirect", "") or self.settings.site_path + "/"
        error    = request.query_params.get("error", "")
        return HTMLResponse(_login_html(error=error, redirect=redirect))

    async def _route_login_post(self, request: Request):
        form     = await request.form()
        email    = str(form.get("email",    "")).strip()
        password = str(form.get("password", ""))
        redirect = self._safe_redirect(str(form.get("redirect", "")).strip())

        user = await _authenticate_admin(email, password)
        if user is None:
            err_url = (
                f"{self.settings.site_path}/login"
                f"?error=Access+Denied"
                f"&redirect={quote(redirect, safe='')}"
            )
            return RedirectResponse(url=err_url, status_code=303)

        # Prevent session fixation: discard any existing session data before
        # writing the newly authenticated user's identity.
        request.session.clear()
        request.session[_SESSION_UID]  = str(user.id)
        request.session[_SESSION_LAST] = datetime.now(timezone.utc).timestamp()
        return RedirectResponse(url=redirect, status_code=303)

    async def _route_logout(self, request: Request) -> RedirectResponse:
        request.session.clear()
        return RedirectResponse(url=f"{self.settings.site_path}/login", status_code=303)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _safe_redirect(self, redirect: str) -> str:
        """Reject open-redirect attempts by ensuring the target is inside /admin."""
        site = self.settings.site_path
        if redirect and redirect.startswith(site):
            return redirect
        return site + "/"
