from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from backend.models import JobStatus, CertificateStatus

class RecipientInput(BaseModel):
    name: str = Field(..., description="Full name of recipient", min_length=1, max_length=150)
    email: Optional[str] = Field(None, description="Optional email address")

    @field_validator("name")
    @classmethod
    def validate_name_not_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Recipient name cannot be empty or whitespace only")
        return trimmed

class JobCreateRequest(BaseModel):
    event_name: str = Field(..., description="Name of the event, course, or program", min_length=1, max_length=200)
    issue_date: Optional[str] = Field(None, description="Date formatted as string, e.g. 'October 7, 2026'")
    recipients: List[RecipientInput] = Field(..., description="List of recipients to generate certificates for", min_length=1)

    @field_validator("event_name")
    @classmethod
    def validate_event_not_blank(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Event name cannot be empty or whitespace only")
        return trimmed

class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_name: str
    recipient_email: Optional[str] = None
    status: CertificateStatus
    error_message: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime

class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    issue_date: Optional[str] = None
    status: JobStatus
    total_count: int
    success_count: int
    failed_count: int
    progress_percentage: float = 0.0
    created_at: datetime
    completed_at: Optional[datetime] = None
    certificates: Optional[List[CertificateResponse]] = None

class JobListResponse(BaseModel):
    jobs: List[JobStatusResponse]
    total: int
