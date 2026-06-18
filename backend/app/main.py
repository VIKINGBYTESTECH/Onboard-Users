import html
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi import Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from .admin_auth import require_user_administrator
from .config import get_settings
from .graph import GraphProvisioner
from .options import OnboardingOptions, load_options, save_options
from .rules import STATUS_COMPLETED, STATUS_PARTIAL, STATUS_WAITING, build_report
from .schemas import OnboardingReport, OnboardingRequest
from .setup import SetupPayload, SetupStatus, reopen_setup, save_setup, setup_status

settings = get_settings()
app = FastAPI(title="IT Onboarding API")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETUP_GUIDE_PATH = PROJECT_ROOT / "docs" / "HOW_TO_SETUP.md"

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


def _render_markdown_page(markdown: str) -> str:
    body: list[str] = []
    in_code = False
    in_list = False

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_code:
                body.append("</code></pre>")
                in_code = False
            else:
                if in_list:
                    body.append("</ul>")
                    in_list = False
                body.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            body.append(html.escape(line) + "\n")
            continue
        if not line:
            if in_list:
                body.append("</ul>")
                in_list = False
            continue
        if line.startswith("# "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("### "):
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("- "):
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{html.escape(line[2:])}</li>")
        else:
            if in_list:
                body.append("</ul>")
                in_list = False
            body.append(f"<p>{html.escape(line)}</p>")

    if in_code:
        body.append("</code></pre>")
    if in_list:
        body.append("</ul>")

    return f"""<!doctype html>
<html lang="no">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Setup guide</title>
  <style>
    body {{
      background: #eef2f5;
      color: #172026;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.55;
      margin: 0;
      padding: 28px;
    }}
    main {{
      background: #fff;
      border: 1px solid #d8e0e7;
      border-radius: 8px;
      margin: 0 auto;
      max-width: 980px;
      padding: 28px;
    }}
    h1, h2, h3 {{ line-height: 1.2; }}
    h1 {{ margin-top: 0; }}
    h2 {{ border-top: 1px solid #e5eaef; margin-top: 28px; padding-top: 22px; }}
    code, pre {{
      background: #f4f7f9;
      border-radius: 7px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    code {{ padding: 1px 4px; }}
    pre {{ overflow-x: auto; padding: 12px; }}
    pre code {{ background: transparent; padding: 0; }}
    li {{ margin: 5px 0; }}
  </style>
</head>
<body>
  <main>
    {''.join(body)}
  </main>
</body>
</html>"""


@app.get("/help/setup", response_class=HTMLResponse)
def setup_help() -> HTMLResponse:
    if not SETUP_GUIDE_PATH.exists():
        raise HTTPException(status_code=404, detail="Setup guide not found.")
    return HTMLResponse(_render_markdown_page(SETUP_GUIDE_PATH.read_text(encoding="utf-8")))


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


@app.post("/api/setup/reopen", response_model=SetupStatus)
def post_setup_reopen() -> SetupStatus:
    try:
        return reopen_setup(settings)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/setup/reopen")
def get_setup_reopen() -> RedirectResponse:
    try:
        reopen_setup(settings)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return RedirectResponse(settings.frontend_origin)


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
