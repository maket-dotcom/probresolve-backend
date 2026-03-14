import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.escalation import ESCALATION_MAP, FALLBACK_ESCALATION
from app.models import Company
from app.schemas import (
    CategoryEmbed,
    CompanyEmbed,
    DomainEmbed,
    EscalationLink,
    EvidenceOut,
    ProblemDetailResponse,
    ProblemListItemV2,
)
from app.services import category_service, problem_service
from app.services.report_service import has_reported, report_problem
from app.services.upvote_service import compute_fingerprint, has_voted, upvote

router = APIRouter(prefix="/api")


async def _build_problem_list(problems, db: AsyncSession) -> list[ProblemListItemV2]:
    report_counts = await problem_service.get_report_counts(db, [p.id for p in problems])
    return [
        ProblemListItemV2(
            id=p.id,
            title=p.title,
            slug=p.slug,
            domain=DomainEmbed.model_validate(p.domain),
            category=CategoryEmbed.model_validate(p.category) if p.category else None,
            company=CompanyEmbed.model_validate(p.company) if p.company else None,
            is_resolved=p.is_resolved,
            is_verified=p.is_verified,
            flags_cleared=p.flags_cleared,
            upvote_count=p.upvote_count,
            report_count=report_counts.get(p.id, 0),
            amount_lost=p.amount_lost,
            poster_name=p.poster_name,
            location_state=p.location_state,
            date_of_incident=p.date_of_incident,
            created_at=p.created_at,
        )
        for p in problems
    ]


@router.get("/domains", response_model=list[DomainEmbed])
async def get_domains(db: AsyncSession = Depends(get_db)):
    domains = await category_service.get_all_domains(db)
    return domains


@router.get("/domains/{domain_id}/categories", response_model=list[CategoryEmbed])
async def get_categories(domain_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    categories = await category_service.get_categories_for_domain(db, domain_id)
    return categories


@router.get("/problems", response_model=list[ProblemListItemV2])
async def list_problems(
    domain_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    problems = await problem_service.list_problems(db, domain_id=domain_id, page=page)
    return await _build_problem_list(problems, db)


@router.get("/problems/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    problem = await problem_service.get_problem(db, problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Read forwarded IP + UA from Next.js server component headers
    ip = request.headers.get("X-Real-IP") or (
        request.client.host if request.client else "unknown"
    )
    ua = request.headers.get("User-Agent", "")
    fingerprint = compute_fingerprint(ip, ua)

    already_voted = await has_voted(db, problem_id, fingerprint)
    already_reported = await has_reported(db, problem_id, fingerprint)
    report_counts = await problem_service.get_report_counts(db, [problem_id])
    report_count = report_counts.get(problem_id, 0)

    domain_slug = problem.domain.slug if problem.domain else ""
    raw_links = ESCALATION_MAP.get(domain_slug, FALLBACK_ESCALATION)
    escalation_links = [
        EscalationLink(name=name, url=url, description=desc)
        for name, url, desc in raw_links
    ]

    return ProblemDetailResponse(
        id=problem.id,
        title=problem.title,
        slug=problem.slug,
        domain=DomainEmbed.model_validate(problem.domain),
        category=CategoryEmbed.model_validate(problem.category) if problem.category else None,
        company=CompanyEmbed.model_validate(problem.company) if problem.company else None,
        description=problem.description,
        is_resolved=problem.is_resolved,
        is_verified=problem.is_verified,
        flags_cleared=problem.flags_cleared,
        upvote_count=problem.upvote_count,
        report_count=report_count,
        amount_lost=problem.amount_lost,
        poster_name=problem.poster_name,
        location_state=problem.location_state,
        date_of_incident=problem.date_of_incident,
        created_at=problem.created_at,
        evidence=[EvidenceOut.model_validate(e) for e in problem.evidence],
        has_email=problem.poster_email is not None,
        already_voted=already_voted,
        already_reported=already_reported,
        escalation_links=escalation_links,
    )


@router.post("/problems/{problem_id}/upvote")
async def upvote_problem(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    ip = request.headers.get("X-Real-IP") or (
        request.client.host if request.client else "unknown"
    )
    ua = request.headers.get("User-Agent", "")
    fingerprint = compute_fingerprint(ip, ua)
    count, already_voted = await upvote(db, problem_id, fingerprint)
    return {"upvote_count": count, "already_voted": already_voted}


@router.post("/problems/{problem_id}/report")
async def report_problem_api(
    request: Request,
    problem_id: uuid.UUID,
    reason: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    ip = request.headers.get("X-Real-IP") or (
        request.client.host if request.client else "unknown"
    )
    ua = request.headers.get("User-Agent", "")
    fingerprint = compute_fingerprint(ip, ua)
    count, _ = await report_problem(db, problem_id, fingerprint, reason)
    return {"report_count": count, "already_reported": True}


@router.get("/search", response_model=list[ProblemListItemV2])
async def search_problems(
    q: str = "",
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
):
    if not q.strip():
        return []
    problems = await problem_service.search_problems(db, q.strip(), page=page)
    return await _build_problem_list(problems, db)


@router.get("/companies", response_model=list[CompanyEmbed])
async def search_companies(
    q: str = "",
    domain_id: str = "",
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Company).order_by(Company.name)
    if domain_id.strip():
        try:
            did = uuid.UUID(domain_id.strip())
            stmt = stmt.where(Company.domain_id == did)
        except ValueError:
            pass
    if q.strip():
        stmt = stmt.where(Company.name.ilike(f"%{q.strip()}%"))
    stmt = stmt.limit(50)
    result = await db.execute(stmt)
    return [CompanyEmbed.model_validate(c) for c in result.scalars().all()]
