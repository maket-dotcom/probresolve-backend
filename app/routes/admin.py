import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.deps import get_db
from app.models import Problem
from app.services.problem_service import (
    delete_problem,
    get_all_problems_admin,
    get_report_counts,
)

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="app/templates")


def _check_admin(request: Request) -> None:
    if request.query_params.get("key") != settings.admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None),
):
    _check_admin(request)
    problems = await get_all_problems_admin(db, q=q)
    report_counts = await get_report_counts(db, [p.id for p in problems])
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "problems": problems,
            "report_counts": report_counts,
            "admin_key": request.query_params.get("key"),
            "frontend_url": settings.frontend_url,
            "q": q or "",
        },
    )


@router.post("/problems/{problem_id}/verify")
async def admin_verify(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    # Only verify if poster_email exists
    result = await db.execute(select(Problem).where(Problem.id == problem_id))
    problem = result.scalar_one_or_none()
    if problem and problem.poster_email and problem.poster_phone:
        await db.execute(
            update(Problem).where(Problem.id == problem_id).values(is_verified=True)
        )
        await db.commit()
    key = request.query_params.get("key")
    return RedirectResponse(f"/admin?key={key}", status_code=303)


@router.post("/problems/{problem_id}/hide")
async def admin_hide(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    await db.execute(
        update(Problem).where(Problem.id == problem_id).values(is_hidden=True)
    )
    await db.commit()
    key = request.query_params.get("key")
    return RedirectResponse(f"/admin?key={key}", status_code=303)


@router.post("/problems/{problem_id}/unhide")
async def admin_unhide(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    await db.execute(
        update(Problem).where(Problem.id == problem_id).values(is_hidden=False)
    )
    await db.commit()
    key = request.query_params.get("key")
    return RedirectResponse(f"/admin?key={key}", status_code=303)


@router.post("/problems/{problem_id}/resolve")
async def admin_resolve(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    await db.execute(
        update(Problem).where(Problem.id == problem_id).values(is_resolved=True)
    )
    await db.commit()
    key = request.query_params.get("key")
    return RedirectResponse(f"/admin?key={key}", status_code=303)


@router.post("/problems/{problem_id}/clear-flags")
async def admin_clear_flags(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    await db.execute(
        update(Problem).where(Problem.id == problem_id).values(flags_cleared=True)
    )
    await db.commit()
    key = request.query_params.get("key")
    return RedirectResponse(f"/admin?key={key}", status_code=303)


@router.post("/problems/{problem_id}/delete")
async def admin_delete(
    request: Request,
    problem_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    _check_admin(request)
    deleted = await delete_problem(db, problem_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    key = request.query_params.get("key")
    return RedirectResponse(f"/admin?key={key}", status_code=303)
