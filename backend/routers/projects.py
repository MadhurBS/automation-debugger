from __future__ import annotations

import math
import shutil
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from config import settings
from database import get_db
from models import LogFile, Project, User
from schemas import DetectPlatformResponse, LogFileResponse, MessageResponse, PasteErrorRequest, ProjectListResponse, ProjectResponse
from services.log_analyzer import LogAnalyzer
from services.project_parser import ProjectParser

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/detect-platform", response_model=DetectPlatformResponse)
async def detect_platform(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a file and get the detected RPA platform without saving a project."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed.")

    # Write to a temp location for analysis
    tmp_dir = Path(settings.UPLOAD_DIR) / f"_tmp_{uuid.uuid4().hex}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    dest = tmp_dir / (file.filename or "upload")

    try:
        async with aiofiles.open(dest, "wb") as f:
            content = await file.read()
            await f.write(content)

        parser = ProjectParser()
        # detect_only runs synchronously in an executor — capture result first,
        # then clean up so the temp dir is still intact during detection.
        result = await parser.detect_only(str(dest))
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(500, f"Detection error: {exc}") from exc

    # Clean up only after result is fully in hand
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return DetectPlatformResponse(
        platform=result["platform"],
        confidence=result["confidence"],
        filename=file.filename or "upload",
    )


@router.post("/upload", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def upload_project(
    request: Request,
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(default=""),
    platform: str = Form(default="unknown"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}")

    # Validate size
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    project_dir = Path(settings.UPLOAD_DIR) / str(uuid.uuid4())
    project_dir.mkdir(parents=True, exist_ok=True)
    dest = project_dir / (file.filename or "upload")

    total = 0
    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                await f.close()
                shutil.rmtree(project_dir, ignore_errors=True)
                raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")
            await f.write(chunk)

    # Always auto-detect; only use the form hint if user explicitly overrode
    parser = ProjectParser()
    parsed = await parser.parse(str(dest), "unknown")

    # If caller supplied an explicit platform override, honour it
    if platform and platform not in ("unknown", ""):
        detected_platform = platform
    else:
        detected_platform = parsed.get("platform", "unknown")

    project = Project(
        name=name or parsed.get("name", file.filename),
        description=description,
        platform=detected_platform,
        upload_path=str(dest),
        original_filename=file.filename or "upload",
        file_size_bytes=total,
        project_metadata=parsed.get("metadata"),
        workflow_structure=parsed.get("workflow_structure"),
        dependencies=parsed.get("dependencies"),
        owner_id=current_user.id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.post("/{project_id}/logs", response_model=list[LogFileResponse], status_code=201)
async def upload_logs(
    project_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    log_dir = Path(settings.UPLOAD_DIR) / str(project_id) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    created = []
    analyzer = LogAnalyzer()
    for upload in files:
        dest = log_dir / (upload.filename or "log.txt")
        async with aiofiles.open(dest, "wb") as f:
            content = await upload.read()
            await f.write(content)

        parsed = await analyzer.analyze(str(dest))

        log_file = LogFile(
            project_id=project_id,
            filename=upload.filename or "log.txt",
            file_path=str(dest),
            log_format=parsed.get("format", "unknown"),
            parsed_entries={"entries": parsed.get("entries", [])},
            exception_summary=parsed.get("exception_summary"),
            execution_trace={"trace": parsed.get("execution_trace", [])},
            error_count=parsed.get("error_count", 0),
            warning_count=parsed.get("warning_count", 0),
        )
        db.add(log_file)
        created.append(log_file)

    await db.commit()
    for lf in created:
        await db.refresh(lf)
    return created


@router.post("/paste-error", response_model=LogFileResponse, status_code=201)
async def paste_error_text(
    payload: PasteErrorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Accept a pasted error message / stack trace and store it as a virtual log file."""
    result = await db.execute(select(Project).where(Project.id == payload.project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    # Write the pasted text to disk so the analyzer can process it normally
    log_dir = Path(settings.UPLOAD_DIR) / str(payload.project_id) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    dest = log_dir / f"pasted_error_{uuid.uuid4().hex[:8]}.txt"
    async with aiofiles.open(dest, "w", encoding="utf-8") as f:
        await f.write(payload.error_text)

    analyzer = LogAnalyzer()
    parsed = await analyzer.analyze(str(dest))

    log_file = LogFile(
        project_id=payload.project_id,
        filename=dest.name,
        file_path=str(dest),
        log_format=parsed.get("format", "text"),
        parsed_entries={"entries": parsed.get("entries", [])},
        exception_summary=parsed.get("exception_summary"),
        execution_trace={"trace": parsed.get("execution_trace", [])},
        error_count=parsed.get("error_count", 0),
        warning_count=parsed.get("warning_count", 0),
    )
    db.add(log_file)
    await db.commit()
    await db.refresh(log_file)
    return log_file


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    page: int = 1,
    size: int = 20,
    platform: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.owner_id == current_user.id)
    if platform:
        query = query.where(Project.platform == platform)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    items_result = await db.execute(query.offset((page - 1) * size).limit(size).order_by(Project.created_at.desc()))
    items = list(items_result.scalars().all())

    return ProjectListResponse(items=items, total=total, page=page, size=size, pages=math.ceil(total / size) if total else 1)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.delete("/{project_id}", response_model=MessageResponse)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == project_id, Project.owner_id == current_user.id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")

    upload_dir = Path(project.upload_path).parent
    shutil.rmtree(upload_dir, ignore_errors=True)

    await db.delete(project)
    await db.commit()
    return MessageResponse(message="Project deleted successfully")
