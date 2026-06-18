from pathlib import Path

from pydantic import BaseModel, Field

from .config import Settings
from .options import OnboardingOptions, load_options, save_options


class SetupStatus(BaseModel):
    enabled: bool
    complete: bool
    needs_setup: bool
    restart_required: bool = False
    options: OnboardingOptions


class SetupRuntime(BaseModel):
    frontend_origin: str = "https://localhost:5174"
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_client_secret: str = ""
    entra_default_domain: str = "example.com"
    entra_usage_location: str = "NO"
    onboarding_portal_url: str = "https://onboarding.example.com"
    it_contact_email: str = "it@example.com"
    send_password_by_email: bool = False


class SetupPayload(BaseModel):
    runtime: SetupRuntime = Field(default_factory=SetupRuntime)
    options: OnboardingOptions


def setup_complete(settings: Settings) -> bool:
    return Path(settings.setup_lock_path).exists()


def setup_status(settings: Settings) -> SetupStatus:
    complete = setup_complete(settings)
    return SetupStatus(
        enabled=settings.setup_wizard_enabled,
        complete=complete,
        needs_setup=settings.setup_wizard_enabled and not complete,
        options=load_options(settings),
    )


def save_setup(settings: Settings, payload: SetupPayload) -> SetupStatus:
    if not settings.setup_wizard_enabled:
        raise PermissionError("Setup wizard is disabled.")
    if setup_complete(settings):
        raise PermissionError("Setup has already been completed.")

    save_options(settings, payload.options)
    Path(settings.backend_env_path).write_text(render_env(payload.runtime), encoding="utf-8")
    Path(settings.setup_lock_path).write_text("complete\n", encoding="utf-8")
    status = setup_status(settings)
    status.restart_required = True
    return status


def reopen_setup(settings: Settings) -> SetupStatus:
    if not settings.setup_wizard_enabled:
        raise PermissionError("Setup wizard is disabled.")

    Path(settings.setup_lock_path).unlink(missing_ok=True)
    return setup_status(settings)


def render_env(runtime: SetupRuntime) -> str:
    return "\n".join(
        [
            f"FRONTEND_ORIGIN={runtime.frontend_origin}",
            r"FRONTEND_ORIGIN_REGEX=^https?://(localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[a-zA-Z0-9.-]+\.ts\.net):5174$",
            f"ENTRA_TENANT_ID={runtime.entra_tenant_id}",
            f"ENTRA_CLIENT_ID={runtime.entra_client_id}",
            f"ENTRA_CLIENT_SECRET={runtime.entra_client_secret}",
            f"ENTRA_DEFAULT_DOMAIN={runtime.entra_default_domain}",
            f"ENTRA_USAGE_LOCATION={runtime.entra_usage_location}",
            "OPTIONS_PATH=app/data/options.json",
            f"ONBOARDING_PORTAL_URL={runtime.onboarding_portal_url}",
            f"IT_CONTACT_EMAIL={runtime.it_contact_email}",
            f"SEND_PASSWORD_BY_EMAIL={str(runtime.send_password_by_email).lower()}",
            "ADMIN_AUTH_DISABLED=false",
            "SETUP_WIZARD_ENABLED=true",
            "",
        ]
    )
