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
    domain_id: uuid.UUID | None = None,
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
    if domain_id is not None:
        stmt = stmt.where(Problem.domain_id == domain_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_scoreboard(
    db: AsyncSession,
    domain_id: uuid.UUID | None = None,
    sort: str = "complaints",
) -> list[dict]:
    """Return companies ranked by complaint count or total ₹ lost.

    Filters on Problem.domain_id (not Company.domain_id) so the results
    answer "companies with complaints IN this domain".
    Hidden problems are excluded.
    """
    from app.models import Company, Domain

    order_col = (
        func.coalesce(func.sum(Problem.amount_lost), 0).desc()
        if sort == "amount"
        else func.count(Problem.id).desc()
    )

    stmt = (
        select(
            Company.id,
            Company.name,
            Company.domain_id,
            func.count(Problem.id).label("complaint_count"),
            func.coalesce(func.sum(Problem.amount_lost), 0).label("total_amount_lost"),
        )
        .join(Problem, Problem.company_id == Company.id)
        .where(Problem.is_hidden == False)  # noqa: E712
        .group_by(Company.id, Company.name, Company.domain_id)
        .having(func.count(Problem.id) > 0)
        .order_by(order_col)
    )
    if domain_id is not None:
        stmt = stmt.where(Problem.domain_id == domain_id)

    result = await db.execute(stmt)
    rows = result.all()

    # Fetch all domains in a single query (few rows) and join in Python
    domain_result = await db.execute(select(Domain))
    domain_map = {d.id: d for d in domain_result.scalars().all()}

    return [
        {
            "id": row.id,
            "name": row.name,
            "domain": domain_map.get(row.domain_id),
            "complaint_count": row.complaint_count,
            "total_amount_lost": int(row.total_amount_lost),
        }
        for row in rows
    ]


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


async def get_company_category_breakdown(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> list[dict]:
    """Return complaint breakdown by category for a single company.

    Groups by Category, sorted by complaint_count descending.
    Problems with no category are grouped under "Uncategorized" (id=None).
    Hidden problems are excluded.
    """
    from app.models import Category

    stmt = (
        select(
            Category.id,
            Category.name,
            func.count(Problem.id).label("complaint_count"),
            func.coalesce(func.sum(Problem.amount_lost), 0).label("total_amount_lost"),
        )
        .select_from(Problem)
        .outerjoin(Category, Problem.category_id == Category.id)
        .where(
            Problem.company_id == company_id,
            Problem.is_hidden == False,  # noqa: E712
        )
        .group_by(Category.id, Category.name)
        .order_by(func.count(Problem.id).desc())
    )
    result = await db.execute(stmt)
    return [
        {
            "id": row.id,                   # None when category_id was NULL
            "name": row.name or "Uncategorized",
            "complaint_count": row.complaint_count,
            "total_amount_lost": int(row.total_amount_lost),
        }
        for row in result.all()
    ]


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
