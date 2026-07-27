from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    JSON,
)
from sqlalchemy.types import Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class PlatformEnum(str, enum.Enum):
    UIPATH = "uipath"
    POWER_AUTOMATE = "power_automate"
    BLUE_PRISM = "blue_prism"
    AUTOMATION_ANYWHERE = "automation_anywhere"
    UNKNOWN = "unknown"


class AnalysisStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class UserRoleEnum(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRoleEnum] = mapped_column(Enum(UserRoleEnum), default=UserRoleEnum.ANALYST)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    projects: Mapped[list[Project]] = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum), default=PlatformEnum.UNKNOWN)
    upload_path: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    project_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    workflow_structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship("User", back_populates="projects")
    log_files: Mapped[list[LogFile]] = relationship("LogFile", back_populates="project", cascade="all, delete-orphan")
    analysis_reports: Mapped[list[AnalysisReport]] = relationship(
        "AnalysisReport", back_populates="project", cascade="all, delete-orphan"
    )


class LogFile(Base):
    __tablename__ = "log_files"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    log_format: Mapped[str] = mapped_column(String(50), default="unknown")
    parsed_entries: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exception_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    execution_trace: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship("Project", back_populates="log_files")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    status: Mapped[AnalysisStatusEnum] = mapped_column(Enum(AnalysisStatusEnum), default=AnalysisStatusEnum.PENDING)
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum), default=PlatformEnum.UNKNOWN)
    root_causes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    standards_violations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    code_errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    standards_score: Mapped[float | None] = mapped_column(nullable=True)
    raw_ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    excel_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_used: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_confidence: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped[Project] = relationship("Project", back_populates="analysis_reports")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User | None] = relationship("User", back_populates="audit_logs")
