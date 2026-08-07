"""Schema-level tests for resume account rules."""

from app.config import settings
from app.models.resume import Resume
from app.schemas.resume import ResumeRead


def test_resume_model_has_no_slot_or_active_columns():
    column_names = set(Resume.__table__.columns.keys())

    assert "slot_number" not in column_names
    assert "is_active" not in column_names
    assert {"id", "user_id", "file_name", "created_at", "updated_at"} <= column_names


def test_resume_limit_is_two():
    assert settings.max_resumes_per_user == 2


def test_resume_response_shape():
    field_names = set(ResumeRead.model_fields)

    assert field_names == {"id", "file_name", "created_at", "updated_at"}
