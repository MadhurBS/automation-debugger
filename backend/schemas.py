from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ──────────────────────────────────────────────────────────────────────────── #
# Auth                                                                          #
# ──────────────────────────────────────────────────────────────────────────── #
class UserRegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# ──────────────────────────────────────────────────────────────────────────── #
# Projects                                                                      #
# ──────────────────────────────────────────────────────────────────────────── #
class WorkflowActivity(BaseModel):
    name: str
    type: str
    display_name: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = None
    children: Optional[List["WorkflowActivity"]] = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    platform: str
    original_filename: str
    file_size_bytes: int
    project_metadata: Optional[Dict[str, Any]] = None
    workflow_structure: Optional[Dict[str, Any]] = None
    dependencies: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DetectPlatformResponse(BaseModel):
    platform: str
    confidence: float
    filename: str


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    page: int
    size: int
    pages: int


# ──────────────────────────────────────────────────────────────────────────── #
# Log Files                                                                     #
# ──────────────────────────────────────────────────────────────────────────── #
class LogEntrySchema(BaseModel):
    timestamp: Optional[str] = None
    level: Optional[str] = None
    message: str
    workflow: Optional[str] = None
    activity: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    raw: Optional[str] = None


class ExceptionDetail(BaseModel):
    type: str
    message: str
    workflow: Optional[str] = None
    activity: Optional[str] = None
    timestamp: Optional[str] = None
    stack_trace: Optional[str] = None
    count: int = 1


class LogFileResponse(BaseModel):
    id: uuid.UUID
    filename: str
    log_format: str
    error_count: int
    warning_count: int
    exception_summary: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────────────────────────────────── #
# Analysis / RCA                                                                #
# ──────────────────────────────────────────────────────────────────────────── #
class RootCause(BaseModel):
    category: str
    title: str
    description: str
    severity: str = Field(default="medium", pattern="^(critical|high|medium|low)$")
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: List[str] = []
    affected_workflow: Optional[str] = None
    affected_activity: Optional[str] = None
    suggested_fix: str = ""
    preventive_recommendations: List[str] = []


class TriggerAnalysisRequest(BaseModel):
    project_id: uuid.UUID
    log_file_ids: Optional[List[uuid.UUID]] = None
    use_ai: bool = True
    check_standards: bool = True


# ──────────────────────────────────────────────────────────────────────────── #
# Paste Error Text                                                              #
# ──────────────────────────────────────────────────────────────────────────── #
class PasteErrorRequest(BaseModel):
    project_id: uuid.UUID
    error_text: str = Field(..., min_length=5, max_length=50_000)


class AnalysisStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class StandardsViolationSchema(BaseModel):
    rule_id: str
    rule_name: str
    severity: str
    description: str
    location: str
    location_type: str
    recommendation: str
    platform: str


class CodeErrorSchema(BaseModel):
    error_type: str
    title: str
    description: str
    severity: str
    location: str
    line_hint: str
    fix: str


class AnalysisReportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    platform: str
    overall_confidence: Optional[float] = None
    ai_used: bool = False
    root_causes: Optional[Dict[str, Any]] = None
    recommendations: Optional[Dict[str, Any]] = None
    standards_violations: Optional[Dict[str, Any]] = None
    code_errors: Optional[Dict[str, Any]] = None
    standards_score: Optional[float] = None
    log_correlation: Optional[Dict[str, Any]] = None
    project_summary: Optional[Dict[str, Any]] = None
    runtime_analysis: Optional[Dict[str, Any]] = None
    has_log: Optional[bool] = False
    rpa_tool: Optional[str] = None
    ai_narrative: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    pdf_path: Optional[str] = None
    excel_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "coerce_numbers_to_str": False}

    @field_validator("has_log", "ai_used", mode="before")
    @classmethod
    def coerce_none_bool(cls, v: Any) -> bool:
        """SQLite stores booleans as 0/1 integers; NULL → False."""
        if v is None:
            return False
        return bool(v)


class AnalysisListResponse(BaseModel):
    items: List[AnalysisReportResponse]
    total: int
    page: int
    size: int
    pages: int


# ──────────────────────────────────────────────────────────────────────────── #
# Generic                                                                       #
# ──────────────────────────────────────────────────────────────────────────── #
class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
