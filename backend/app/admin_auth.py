import time
from functools import lru_cache

import httpx
from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from .config import Settings, get_settings


@lru_cache(maxsize=8)
def _jwks_for_tenant(tenant_id: str) -> tuple[float, dict]:
    url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    response = httpx.get(url, timeout=15)
    response.raise_for_status()
    return time.time(), response.json()


def _get_jwks(settings: Settings) -> dict:
    created_at, jwks = _jwks_for_tenant(settings.entra_tenant_id)
    if time.time() - created_at > 3600:
        _jwks_for_tenant.cache_clear()
        _, jwks = _jwks_for_tenant(settings.entra_tenant_id)
    return jwks


def require_user_administrator(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> dict:
    if settings.admin_auth_disabled:
        return {"name": "Local admin bypass", "roles": ["User Administrator"]}

    if not settings.entra_tenant_id or not settings.entra_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin authentication requires ENTRA_TENANT_ID and ENTRA_CLIENT_ID.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        header = jwt.get_unverified_header(token)
        jwks = _get_jwks(settings)
        key = next((item for item in jwks["keys"] if item["kid"] == header["kid"]), None)
        if not key:
            _jwks_for_tenant.cache_clear()
            jwks = _get_jwks(settings)
            key = next((item for item in jwks["keys"] if item["kid"] == header["kid"]), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token signing key not found.")
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.entra_client_id,
            options={"verify_iss": False},
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc

    if claims.get("tid") != settings.entra_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token tenant is not allowed.")

    directory_roles = claims.get("wids", [])
    app_roles = claims.get("roles", [])
    has_user_admin = (
        settings.user_administrator_role_template_id in directory_roles
        or "User Administrator" in app_roles
    )
    if not has_user_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User Administrator role required.")
    return claims
