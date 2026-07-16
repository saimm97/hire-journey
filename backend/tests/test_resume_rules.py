"""Schema-level tests for resume account invariants."""

from app.models.resume import Resume
from app.schemas.resume import ResumeRead


def test_resume_model_declares_slot_and_active_constraints():
    constraint_names = {constraint.name for constraint in Resume.__table__.constraints}
    index_names = {index.name for index in Resume.__table__.indexes}

    assert "ck_resumes_slot_number" in constraint_names
    assert "uq_resumes_user_slot" in constraint_names
    assert "uq_resumes_one_active_per_user" in index_names


def test_resume_response_exposes_slot_and_active_state():
    field_names = set(ResumeRead.model_fields)

    assert {"resume_id", "slot_number", "is_active", "updated_at"} <= field_names
