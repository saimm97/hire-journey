"""Resume account-management schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_name: str
    created_at: datetime
    updated_at: datetime
