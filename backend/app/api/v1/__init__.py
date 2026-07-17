from fastapi import APIRouter

from app.api.v1 import (
    auth,
    evaluations,
    jobs,
    notes,
    profile,
    resumes,
    search,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(profile.router, prefix="/profile", tags=["profile"])
router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(search.router, prefix="/search", tags=["search"])
router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
router.include_router(notes.router, prefix="/notes", tags=["notes"])
