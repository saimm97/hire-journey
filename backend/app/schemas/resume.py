"""Resume account-management schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resume_id: uuid.UUID
    slot_number: int
    file_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
