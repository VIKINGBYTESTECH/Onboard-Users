import re
import secrets
import string
import unicodedata
from datetime import date

from .config import Settings
from .options import load_options
from .schemas import OnboardingInput, OnboardingReport, OnboardingRequest

STATUS_COMPLETED = "Fullført"
STATUS_PARTIAL = "Delvis fullført"
STATUS_WAITING = "Avventer"

DEPARTMENT_GROUPS = {
    "it": ["IT-Users", "VPN-Users", "Intune-Managed"],
    "økonomi": ["Finance", "ERP-Users"],
    "okonomi": ["Finance", "ERP-Users"],
    "finance": ["Finance", "ERP-Users"],
    "salg": ["CRM-Users", "Sales-Team"],
    "sales": ["CRM-Users", "Sales-Team"],
}

DEPARTMENT_TEAMS = {
    "it": ["IT"],
    "økonomi": ["Økonomi"],
    "okonomi": ["Økonomi"],
    "finance": ["Økonomi"],
    "salg": ["Salg"],
    "sales": ["Salg"],
}

STANDARD_TASKS = [
    "Klargjør arbeidsstasjon",
    "Opprett adgangskort",
    "Opprett signatur",
    "Tildel programvare",
    "Bekreft MFA-oppsett",
]


def normalize_key(value: str) -> str:
    value = value.strip().lower()
    folded = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def slug_part(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(ch for ch in folded if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-zA-Z0-9]+", ".", ascii_value.lower()).strip(".")
    return re.sub(r"\.+", ".", cleaned)


def generate_username(full_name: str, domain: str) -> str:
    parts = [part for part in slug_part(full_name).split(".") if part]
    if not parts:
        return f"user@{domain}"
    if len(parts) == 1:
        local_part = parts[0]
    else:
        local_part = f"{parts[0]}.{parts[-1]}"
    return f"{local_part}@{domain}"


def generate_password(length: int = 18) -> str:
    alphabet = string.ascii_letters + string.digits + "!#%&?"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(ch.islower() for ch in password)
            and any(ch.isupper() for ch in password)
            and any(ch.isdigit() for ch in password)
            and any(ch in "!#%&?" for ch in password)
        ):
            return password


def parse_start_date(value: str) -> list[str]:
    try:
        date.fromisoformat(value)
    except ValueError:
        return ["Startdato må være ISO-format YYYY-MM-DD."]
    return []


def validate_against_options(employee: OnboardingInput, settings: Settings) -> list[str]:
    options = load_options(settings)
    errors = []
    allowed = {
        "Firma": (employee.company, options.companies),
        "Avdeling": (employee.department, options.departments),
        "Kontorsted": (employee.office_location, options.office_locations),
        "Ansatttype": (employee.employee_type, options.employee_types),
        "Behov for PC": (employee.needs_pc, ["Ja", "Nei"]),
        "Behov for mobil": (employee.needs_mobile, ["Ja", "Nei"]),
    }
    for label, (value, values) in allowed.items():
        if value not in values:
            errors.append(f"{label} må være en av: {', '.join(values)}.")
    return errors


def groups_for(employee: OnboardingInput) -> tuple[list[str], list[str]]:
    key = normalize_key(employee.department)
    groups = DEPARTMENT_GROUPS.get(key, [])
    deviations = []
    if not groups:
        deviations.append(f"Ukjent avdelingsmapping for '{employee.department}'. Ingen utvidede grupper foreslått.")
    return groups, deviations


def licenses_for(employee: OnboardingInput) -> list[str]:
    licenses = ["Microsoft 365 Business Premium"]
    title = normalize_key(employee.job_title)
    department = normalize_key(employee.department)
    if "leder" in title or "manager" in title or "head of" in title:
        licenses.append("Power BI Pro")
    if department == "it":
        licenses.extend(["Intune", "Defender for Endpoint"])
    return list(dict.fromkeys(licenses))


def access_for(employee: OnboardingInput) -> tuple[list[str], list[str], list[str]]:
    key = normalize_key(employee.department)
    teams = DEPARTMENT_TEAMS.get(key, [])
    sharepoint = [f"SharePoint-{employee.department}"] if teams else []
    distribution = [f"{slug_part(employee.department)}@example.com"] if teams else []
    return teams, sharepoint, distribution


def equipment_for(employee: OnboardingInput) -> list[str]:
    equipment = []
    title = normalize_key(employee.job_title)
    if employee.needs_pc == "Ja":
        pc_model = "Standard laptop"
        if "utvikler" in title or "developer" in title or "it" in normalize_key(employee.department):
            pc_model = "Developer laptop"
        elif "leder" in title or "manager" in title:
            pc_model = "Manager laptop"
        equipment.append(f"PC-bestilling: {pc_model}, Intune-registrering klargjøres, serienummer avventer.")
    if employee.needs_mobile == "Ja":
        equipment.append("Mobilbestilling: abonnement tildeles, IMEI avventer.")
    return equipment


def tasks_for(employee: OnboardingInput) -> list[str]:
    tasks = STANDARD_TASKS.copy()
    if employee.needs_mobile == "Ja":
        tasks.insert(2, "Bestill mobil")
    return tasks


def welcome_email(employee: OnboardingInput, username: str, password: str | None, settings: Settings) -> str:
    password_line = (
        f"Midlertidig passord: {password}"
        if password and settings.send_password_by_email
        else "Midlertidig passord deles via godkjent sikker kanal."
    )
    return (
        f"Hei {employee.full_name},\n\n"
        "Velkommen til selskapet. Vi gleder oss til å ha deg med på laget.\n\n"
        f"Startdato: {employee.start_date}\n"
        f"Brukernavn: {username}\n"
        f"{password_line}\n"
        f"Onboardingportal: {settings.onboarding_portal_url}\n\n"
        "Ved første innlogging må du bytte passord og sette opp MFA. "
        "Følg veiledningen i onboardingportalen.\n\n"
        f"Kontakt IT ved behov: {settings.it_contact_email}\n\n"
        "Vennlig hilsen\nIT"
    )


def build_report(request: OnboardingRequest, settings: Settings, include_password: bool) -> OnboardingReport:
    employee = request.employee
    approvals = request.approvals
    errors = parse_start_date(employee.start_date)
    errors.extend(validate_against_options(employee, settings))
    deviations: list[str] = []
    audit_log = ["Mottok HR-data.", "Validerte obligatoriske felt og kontrollerte verdier."]

    username = generate_username(employee.full_name, settings.entra_default_domain)
    password = generate_password() if include_password else None
    groups, group_deviations = groups_for(employee)
    deviations.extend(group_deviations)
    licenses = licenses_for(employee)
    teams, sharepoint_groups, distribution_lists = access_for(employee)
    equipment = equipment_for(employee)
    tasks = tasks_for(employee)

    if not approvals.hr_approved:
        errors.append("HR-godkjenning mangler.")
    if not approvals.manager_approved:
        errors.append("Ledergodkjenning mangler.")
    if approvals.execute and not settings.graph_configured:
        errors.append("Entra/Graph er ikke konfigurert med tenant, client ID og client secret.")

    next_steps = []
    if errors:
        next_steps.extend(["Korriger mangler og innhent nødvendige godkjenninger."])
    if not approvals.execute:
        next_steps.append("Sett execute=true etter godkjenning for å kjøre faktisk Entra-provisjonering.")
    if deviations:
        next_steps.append("Avklar avvik før utvidede rettigheter tildeles.")
    if not next_steps:
        next_steps.append("Kontroller rapport og send velkomstinformasjon via godkjent kanal.")

    status = STATUS_WAITING if errors or not approvals.execute else STATUS_COMPLETED
    summary = [
        f"Foreslått brukernavn: {username}",
        f"Firma: {employee.company}",
        f"Foreslåtte grupper: {', '.join(groups) if groups else 'Ingen'}",
        f"Foreslåtte lisenser: {', '.join(licenses)}",
        f"Utstyr: {', '.join(equipment) if equipment else 'Ingen bestilling nødvendig'}",
    ]

    if approvals.hr_approved and approvals.manager_approved:
        audit_log.append("HR- og ledergodkjenning registrert.")
    if approvals.execute:
        audit_log.append("Bruker har bedt om faktisk provisjonering.")
    else:
        audit_log.append("Kjører i forhåndsvisning uten irreversible handlinger.")

    return OnboardingReport(
        summary=summary,
        errors=errors,
        deviations=deviations,
        next_steps=next_steps,
        status=status,
        username=username,
        temporary_password=password if include_password else None,
        accounts=[],
        groups=groups,
        licenses=licenses,
        teams=teams,
        sharepoint_groups=sharepoint_groups,
        distribution_lists=distribution_lists,
        equipment=equipment,
        tasks=tasks,
        welcome_email=welcome_email(employee, username, password, settings),
        audit_log=audit_log,
        graph_configured=settings.graph_configured,
        graph_executed=False,
    )
