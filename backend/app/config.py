from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    frontend_origin: str = "https://localhost:5174"
    frontend_origin_regex: str = (
        r"^https?://("
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
        r"[a-zA-Z0-9.-]+\.ts\.net"
        r"):5174$"
    )
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_client_secret: str = ""
    entra_default_domain: str = "example.com"
    entra_usage_location: str = "NO"
    onboarding_portal_url: str = "https://onboarding.example.com"
    it_contact_email: str = "it@example.com"
    send_password_by_email: bool = False
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    options_path: str = "app/data/options.json"
    admin_auth_disabled: bool = False
    setup_wizard_enabled: bool = True
    setup_lock_path: str = ".setup-complete"
    backend_env_path: str = ".env"
    user_administrator_role_template_id: str = "fe930be7-5e62-47db-91af-98c3a49a38b1"

    @property
    def graph_configured(self) -> bool:
        return bool(self.entra_tenant_id and self.entra_client_id and self.entra_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
