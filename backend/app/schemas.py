from typing import Any

from pydantic import BaseModel, Field


class OnboardingInput(BaseModel):
    full_name: str = Field(..., min_length=1)
    company: str = Field(..., min_length=1)
    job_title: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    manager: str = Field(..., min_length=1)
    office_location: str = Field(..., min_length=1)
    start_date: str = Field(..., min_length=1)
    employee_type: str = Field(..., min_length=1)
    needs_pc: str = Field(..., min_length=1)
    needs_mobile: str = Field(..., min_length=1)


class ApprovalState(BaseModel):
    hr_approved: bool = False
    manager_approved: bool = False
    execute: bool = False


class OnboardingRequest(BaseModel):
    employee: OnboardingInput
    approvals: ApprovalState = Field(default_factory=ApprovalState)


class OnboardingReport(BaseModel):
    summary: list[str]
    errors: list[str]
    deviations: list[str]
    next_steps: list[str]
    status: str
    username: str | None = None
    temporary_password: str | None = None
    accounts: list[str]
    groups: list[str]
    licenses: list[str]
    teams: list[str]
    sharepoint_groups: list[str]
    distribution_lists: list[str]
    equipment: list[str]
    tasks: list[str]
    welcome_email: str
    audit_log: list[str]
    graph_configured: bool
    graph_executed: bool
    raw_graph_results: list[dict[str, Any]] = Field(default_factory=list)
