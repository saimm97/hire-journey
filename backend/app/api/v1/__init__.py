from fastapi import APIRouter

from app.api.v1 import auth, profile, resumes

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(profile.router, prefix="/profile", tags=["profile"])
router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
