"""Schema-level tests for resume account rules."""

from app.models.resume import Resume
from app.schemas.resume import ResumeRead
from app.services.resume_service import MAX_RESUMES_PER_USER


def test_resume_model_has_no_slot_or_active_columns():
    column_names = set(Resume.__table__.columns.keys())

    assert "slot_number" not in column_names
    assert "is_active" not in column_names
    assert {"id", "user_id", "file_name", "created_at", "updated_at"} <= column_names


def test_resume_limit_is_two():
    assert MAX_RESUMES_PER_USER == 2


def test_resume_response_shape():
    field_names = set(ResumeRead.model_fields)

    assert field_names == {"id", "file_name", "created_at", "updated_at"}
