from fastapi import FastAPI, HTTPException
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware

from .admin_auth import require_user_administrator
from .config import get_settings
from .graph import GraphProvisioner
from .options import OnboardingOptions, load_options, save_options
from .rules import STATUS_COMPLETED, STATUS_PARTIAL, STATUS_WAITING, build_report
from .schemas import OnboardingReport, OnboardingRequest
from .setup import SetupPayload, SetupStatus, save_setup, setup_status

settings = get_settings()
app = FastAPI(title="IT Onboarding API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_origin_regex=settings.frontend_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/config")
def config() -> dict[str, object]:
    return {
        "graph_configured": settings.graph_configured,
        "default_domain": settings.entra_default_domain,
        "send_password_by_email": settings.send_password_by_email,
        "entra_tenant_id": settings.entra_tenant_id,
        "entra_client_id": settings.entra_client_id,
        "admin_auth_available": bool(settings.entra_tenant_id and settings.entra_client_id),
    }


@app.get("/api/options", response_model=OnboardingOptions)
def options() -> OnboardingOptions:
    return load_options(settings)


@app.get("/api/setup/status", response_model=SetupStatus)
def get_setup_status() -> SetupStatus:
    return setup_status(settings)


@app.post("/api/setup/save", response_model=SetupStatus)
def post_setup(payload: SetupPayload) -> SetupStatus:
    try:
        return save_setup(settings, payload)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/admin/options", response_model=OnboardingOptions)
def admin_options(_: dict = Depends(require_user_administrator)) -> OnboardingOptions:
    return load_options(settings)


@app.put("/api/admin/options", response_model=OnboardingOptions)
def update_admin_options(
    options_payload: OnboardingOptions,
    _: dict = Depends(require_user_administrator),
) -> OnboardingOptions:
    save_options(settings, options_payload)
    return load_options(settings)


@app.post("/api/onboarding/preview", response_model=OnboardingReport)
def preview(request: OnboardingRequest) -> OnboardingReport:
    return build_report(request, settings, include_password=False)


@app.post("/api/onboarding/run", response_model=OnboardingReport)
async def run(request: OnboardingRequest) -> OnboardingReport:
    report = build_report(request, settings, include_password=True)
    if report.errors or not request.approvals.execute:
        report.status = STATUS_WAITING
        return report

    try:
        provisioner = GraphProvisioner(settings)
        results = await provisioner.provision(
            request.employee,
            report.username or "",
            report.temporary_password or "",
            report.groups,
            report.licenses,
        )
        report.raw_graph_results = results
        report.graph_executed = True
        report.accounts = [
            item["userPrincipalName"]
            for item in results
            if item.get("action") == "create_user" and item.get("status") == "created"
        ]
        report.audit_log.extend([f"Graph: {item}" for item in results])
        unresolved = [item for item in results if item.get("status") in {"not_found", "sku_not_found"}]
        if unresolved:
            report.deviations.extend([f"Graph-avvik: {item}" for item in unresolved])
            report.status = STATUS_PARTIAL
        else:
            report.status = STATUS_COMPLETED
        report.next_steps = ["Kontroller MFA-oppsett, utstyr og velkomstinformasjon."]
    except Exception as exc:
        report.errors.append(f"Graph-provisjonering feilet: {exc}")
        report.status = STATUS_PARTIAL
        report.next_steps = ["Undersøk Graph-feil, rett eventuell konfigurasjon, og kjør gjenværende steg manuelt eller på nytt."]
        report.audit_log.append(f"Graph-feil: {exc}")
    return report
