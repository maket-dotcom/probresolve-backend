import uuid

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Problem, Report
from app.schemas import ProblemCreate
from app.services.upload_service import delete_problem_files

PAGE_SIZE = 20


async def create_problem(db: AsyncSession, data: ProblemCreate) -> Problem:
    slug = slugify(data.title, max_length=350, word_boundary=True)

    problem = Problem(
        domain_id=data.domain_id,
        category_id=data.category_id,
        company_id=data.company_id,
        title=data.title,
        slug=slug,
        description=data.description,
        amount_lost=data.amount_lost,  # exact Rupees — no paise conversion
        poster_name=data.poster_name,
        poster_email=data.poster_email,
        poster_phone=data.poster_phone,
        location_state=data.location_state,
        date_of_incident=data.date_of_incident,
    )
    db.add(problem)
    await db.commit()
    await db.refresh(problem)
    return problem


async def get_problem(db: AsyncSession, problem_id: uuid.UUID) -> Problem | None:
    """Returns problem only if not hidden."""
    result = await db.execute(
        select(Problem)
        .options(
            selectinload(Problem.evidence),
            selectinload(Problem.domain),
            selectinload(Problem.category),
            selectinload(Problem.company),
        )
        .where(Problem.id == problem_id, Problem.is_hidden == False)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def list_problems(
    db: AsyncSession,
    domain_id: uuid.UUID | None = None,
    page: int = 1,
) -> list[Problem]:
    offset = (page - 1) * PAGE_SIZE
    stmt = (
        select(Problem)
        .options(selectinload(Problem.domain), selectinload(Problem.category), selectinload(Problem.company))
        .order_by(Problem.created_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    stmt = stmt.where(Problem.is_hidden == False)  # noqa: E712
    if domain_id is not None:
        stmt = stmt.where(Problem.domain_id == domain_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def search_problems(
    db: AsyncSession,
    query: str,
    page: int = 1,
) -> list[Problem]:
    offset = (page - 1) * PAGE_SIZE
    pattern = f"%{query}%"
    stmt = (
        select(Problem)
        .options(selectinload(Problem.domain), selectinload(Problem.category), selectinload(Problem.company))
        .where(
            Problem.is_hidden == False,  # noqa: E712
            Problem.title.ilike(pattern) | Problem.description.ilike(pattern),
        )
        .order_by(Problem.created_at.desc())
        .offset(offset)
        .limit(PAGE_SIZE)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_report_counts(
    db: AsyncSession, problem_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Return {problem_id: report_count} for the given problem IDs."""
    if not problem_ids:
        return {}
    result = await db.execute(
        select(Report.problem_id, func.count(Report.id))
        .where(Report.problem_id.in_(problem_ids))
        .group_by(Report.problem_id)
    )
    return dict(result.all())


async def get_all_problems_admin(db: AsyncSession, q: str | None = None) -> list[Problem]:
    """Return all problems including hidden — for admin use only."""
    stmt = (
        select(Problem)
        .options(
            selectinload(Problem.domain),
            selectinload(Problem.category),
            selectinload(Problem.company),
            selectinload(Problem.evidence),
        )
        .order_by(Problem.created_at.desc())
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Problem.title.ilike(pattern)
            | Problem.description.ilike(pattern)
            | Problem.poster_name.ilike(pattern)
        )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_problem(db: AsyncSession, problem_id: uuid.UUID) -> bool:
    """Hard delete a problem and all its associated Supabase files.

    Deletes Supabase storage files first, then removes the DB record.
    CASCADE on Evidence, Upvote, and Report means dependent rows are
    deleted automatically by the database.
    """
    # Fetch the problem regardless of is_hidden state
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if not problem:
        return False

    # 1. Delete uploaded evidence files from Supabase Storage
    await delete_problem_files(problem_id)

    # 2. Delete the DB record (related rows cascade automatically)
    await db.delete(problem)
    await db.commit()
    return True
