"""Companies and a profile's employment history.

Company identity is shared across profiles, so companies are created but never
deleted here (unlike projects, which can be profile-owned). Employment rows
belong to exactly one profile and are replaced wholesale.
"""

from datetime import date

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.employment import EmploymentHistory
from app.schemas.extraction import EmploymentItem
from app.schemas.profile import EmploymentEntry, EmploymentRead
from app.utils.normalization import clean, clip, normalize_month


def _normalize_company_name(name: str) -> str:
    """Collapse whitespace runs, preserving the display casing."""
    return " ".join(name.split())


async def _get_or_create_company(db: AsyncSession, display_name: str) -> Company:
    """Case-insensitively reuse a company row, creating it if absent.

    The database unique constraint covers only exact names, so "Google" and
    "google" would both pass. A transaction-scoped advisory lock keyed on the
    lowercase name serializes concurrent first-inserts instead. Callers resolve
    companies in sorted-name order so two uploads never acquire overlapping
    locks in opposite order — see replace_employments below, which is the only
    caller and enforces that ordering.
    """
    key = display_name.lower()
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtext(key))))
    company = (
        await db.execute(
            select(Company)
            .where(func.lower(Company.name) == key)
            # Deterministic compatibility rule: prefer a source-linked row,
            # then the oldest employer record.
            .order_by(Company.slug.is_(None), Company.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    if company is not None:
        return company
    company = Company(name=display_name)
    db.add(company)
    await db.flush()
    return company


def _employment_dates(
    entry: EmploymentItem | EmploymentEntry,
) -> tuple[date | None, date | None]:
    start = normalize_month(entry.start_date)
    end = normalize_month(entry.end_date)
    if start and end and end < start:
        # Contradictory order: treat both as unparseable rather than guessing
        # (a null end alone would falsely mark the stint as current).
        return None, None
    return start, end


async def replace_employments(
    db: AsyncSession, profile_id: int, entries: list[EmploymentItem] | list[EmploymentEntry]
) -> None:
    """Replace the profile's employment rows.

    Deletes employment rows only. Company identity is shared across profiles
    and is never deleted here (unlike projects, which can be profile-owned).
    """
    await db.execute(delete(EmploymentHistory).where(EmploymentHistory.profile_id == profile_id))
    valid = [entry for entry in entries if clean(entry.company_name) and clean(entry.title)]
    display_names: dict[str, str] = {}
    for entry in valid:
        display = clip(_normalize_company_name(entry.company_name), 255)
        display_names.setdefault(display.lower(), display)
    companies = {
        key: await _get_or_create_company(db, display_names[key])
        for key in sorted(display_names)  # sorted: consistent advisory-lock order
    }
    seen: set[tuple] = set()
    for entry in valid:
        start_date, end_date = _employment_dates(entry)
        company_key = clip(_normalize_company_name(entry.company_name), 255).lower()
        title = clip(entry.title, 255)
        # Resumes often repeat a stint (e.g. summary + history); keep the first.
        row_key = (company_key, title.lower(), start_date, end_date)
        if row_key in seen:
            continue
        seen.add(row_key)
        db.add(
            EmploymentHistory(
                profile_id=profile_id,
                company_id=companies[company_key].id,
                title=title,
                start_date=start_date,
                end_date=end_date,
                description=clean(entry.description),
            )
        )
    await db.flush()


async def load_employments(db: AsyncSession, profile_id: int) -> list[EmploymentRead]:
    rows = (
        await db.execute(
            select(EmploymentHistory, Company)
            .join(Company, Company.id == EmploymentHistory.company_id)
            .where(EmploymentHistory.profile_id == profile_id)
            .order_by(EmploymentHistory.start_date.desc().nulls_last(), EmploymentHistory.id)
        )
    ).all()
    return [
        EmploymentRead(
            id=employment.id,
            company_name=company.name,
            title=employment.title,
            start_date=employment.start_date,
            end_date=employment.end_date,
            description=employment.description,
        )
        for employment, company in rows
    ]
