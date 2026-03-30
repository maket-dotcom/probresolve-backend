import re
import uuid as _uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.config import MAX_FILE_SIZE, MAX_FILES, MAX_TOTAL_FILE_SIZE
from app.deps import get_db
from app.limiter import limiter
from app.models import Evidence, Company
from app.schemas import ProblemCreate
from app.services import problem_service, upload_service

router = APIRouter(prefix="/api")


def parse_amount_lost(raw: str | None) -> int | None:
    if raw is None or not str(raw).strip():
        return None
    # Truncate at decimal point then strip all non-digits
    text = str(raw).strip().split(".")[0]
    cleaned = re.sub(r"[^0-9]", "", text)
    if not cleaned:
        return None
    value = int(cleaned)
    if value > 1_000_000_000_000:
        raise HTTPException(status_code=422, detail="amount_lost exceeds maximum allowed value.")
    return value


@router.post("/problems")
@limiter.limit("10/minute")
async def create_problem(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()

    # Extract files from the form (single source of truth — no double-read)
    files = [
        v for k, v in form.multi_items()
        if k == "files" and isinstance(v, UploadFile) and v.filename and v.filename != "blob"
    ][:MAX_FILES]

    # Parse amount — prefer amount_lost_raw (pure digits from hidden input), fall back to amount_lost
    amount_raw = form.get("amount_lost_raw") or form.get("amount_lost", "")
    amount_lost = parse_amount_lost(amount_raw)

    # Parse optional date
    date_raw = form.get("date_of_incident", "")
    date_of_incident = (
        date.fromisoformat(str(date_raw)) if date_raw and str(date_raw).strip() else None
    )

    domain_id = _uuid.UUID(str(form.get("domain_id")))
    cat_raw = form.get("category_id", "")
    category_id = _uuid.UUID(str(cat_raw)) if cat_raw and str(cat_raw).strip() else None

    company_name = form.get("company_name", "")
    company_id = None
    if company_name and str(company_name).strip():
        name_clean = str(company_name).strip()
        result = await db.execute(select(Company).where(Company.name.ilike(name_clean)))
        company = result.scalar_one_or_none()
        if not company:
            company = Company(name=name_clean)
            db.add(company)
            await db.flush()  # to get ID
        company_id = company.id

    try:
        data = ProblemCreate(
            domain_id=domain_id,
            category_id=category_id,
            company_id=company_id,
            title=str(form.get("title", "")),
            description=str(form.get("description", "")),
            amount_lost=amount_lost,
            poster_name=str(form.get("poster_name", "")) or None,
            poster_email=str(form.get("poster_email", "")) or None,
            poster_phone=str(form.get("poster_phone", "")) or None,
            location_state=str(form.get("location_state", "")) or None,
            date_of_incident=date_of_incident,
        )
    except ValidationError as exc:
        msgs = "; ".join(e["msg"] for e in exc.errors())
        raise HTTPException(status_code=422, detail=msgs)

    problem = await problem_service.create_problem(db, data)

    # Upload evidence files
    uploaded = 0
    skipped = 0
    total_bytes = 0

    for upload in files:
        content = await upload.read()
        # Skip empty or oversized
        if not content or len(content) > MAX_FILE_SIZE:
            skipped += 1
            continue
        # Check total size limit
        if total_bytes + len(content) > MAX_TOTAL_FILE_SIZE:
            skipped += 1
            continue
        # Skip invalid file types (extension + MIME + magic bytes must all agree)
        if not upload_service.is_valid_file(
            content,
            upload.filename or "",
            upload.content_type or "",
        ):
            skipped += 1
            continue
        # Upload to Supabase
        try:
            file_url = await upload_service.upload_file(
                problem.id,
                content,
                upload.filename,
                upload.content_type or "application/octet-stream",
            )
        except Exception:
            skipped += 1
            continue
        await db.execute(
            insert(Evidence).values(
                problem_id=problem.id,
                file_url=file_url,
                file_name=upload.filename,
                content_type=upload.content_type,
            )
        )
        total_bytes += len(content)
        uploaded += 1

    await db.commit()

    return JSONResponse(
        {"id": str(problem.id), "slug": problem.slug, "uploaded": uploaded, "skipped": skipped},
        status_code=201,
    )
