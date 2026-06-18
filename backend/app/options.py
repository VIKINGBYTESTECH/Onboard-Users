import json
from pathlib import Path

from pydantic import BaseModel, Field

from .config import Settings


class OnboardingOptions(BaseModel):
    companies: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    office_locations: list[str] = Field(default_factory=list)
    employee_types: list[str] = Field(default_factory=list)
    pc_models: list[str] = Field(default_factory=list)
    mobile_subscriptions: list[str] = Field(default_factory=list)


DEFAULT_OPTIONS = OnboardingOptions(
    companies=[
        "Example Company AS",
        "Example Company Sweden AB",
        "Example Company Denmark ApS",
    ],
    departments=["IT", "Finance", "Sales", "HR", "Operations"],
    office_locations=["Oslo", "Stockholm", "Copenhagen", "Remote"],
    employee_types=["Fast", "Midlertidig", "Konsulent"],
    pc_models=["Standard laptop", "Developer laptop", "Manager laptop"],
    mobile_subscriptions=["Standard mobil", "Data pluss", "Ingen"],
)


def options_path(settings: Settings) -> Path:
    return Path(settings.options_path)


def load_options(settings: Settings) -> OnboardingOptions:
    path = options_path(settings)
    if not path.exists():
        save_options(settings, DEFAULT_OPTIONS)
        return DEFAULT_OPTIONS
    return OnboardingOptions.model_validate_json(path.read_text(encoding="utf-8"))


def save_options(settings: Settings, options: OnboardingOptions) -> None:
    cleaned = OnboardingOptions(
        companies=clean_list(options.companies),
        departments=clean_list(options.departments),
        office_locations=clean_list(options.office_locations),
        employee_types=clean_list(options.employee_types),
        pc_models=clean_list(options.pc_models),
        mobile_subscriptions=clean_list(options.mobile_subscriptions),
    )
    path = options_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cleaned.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def clean_list(values: list[str]) -> list[str]:
    seen = set()
    cleaned = []
    for value in values:
        item = value.strip()
        key = item.casefold()
        if item and key not in seen:
            cleaned.append(item)
            seen.add(key)
    return cleaned
