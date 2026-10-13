"""Demo session helper: role resolution + backend permission guard.

The session is a demo role carried on `?as=` or the `tt_role` cookie,
defaulting to the read-only verifier. `guard()` enforces permissions on the
backend and renders a 403 page on denial — UI hiding is never the boundary.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.services import deps
from app.services.mock_access import ForbiddenError

templates = Jinja2Templates(directory="templates")

SESSION_COOKIE = "tt_role"


def current_role(request: Request) -> str:
    query_role = request.query_params.get("as")
    if query_role:
        return deps.access_role_id(query_role)
    return deps.access_role_id(request.cookies.get(SESSION_COOKIE))


def session_context(request: Request) -> dict[str, object]:
    role_id = current_role(request)
    user = deps.access_overview(role_id).current_user
    return {
        "demo": config.is_demo(),
        "chain_label": config.chain_label(),
        "role_id": role_id,
        "role_name": deps.access_overview(role_id).current_role.name,
        "user_name": user.name,
        "user_org": user.organization,
    }


def guard(
    request: Request,
    permission: str,
    target: str = "",
    active: str = "access",
) -> HTMLResponse | None:
    """Require a permission for the current demo session.

    Returns None when allowed (and records the audit entry), otherwise a
    403 response that names the missing permission without leaking data.
    """
    role_id = current_role(request)
    try:
        deps.access_require(role_id, permission, target)
    except ForbiddenError as exc:
        data = deps.access_overview(role_id)
        return templates.TemplateResponse(
            request,
            "pages/forbidden.html",
            {**session_context(request), "active": active,
             "permission": exc.permission, "role": data.current_role,
             "target": target},
            status_code=403,
        )
    deps.access_record_allowed(role_id, permission, target)
    return None
