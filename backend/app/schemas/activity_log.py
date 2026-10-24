from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ActivityLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    action_type: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    occurred_at: Optional[datetime] = None
    metadata: Optional[Union[Dict[str, Any], str]] = Field(default=None, alias="metadata_json")

    @field_validator("metadata", mode="before")
    @classmethod
    def coerce_metadata(cls, v):
        """Ensure metadata is always a dict or None, even if stored as a plain string."""
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # If not parseable as JSON dict, wrap as a description dict
            return {"description": v}
        return v

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedActivityLogResponse(BaseModel):
    items: List[ActivityLogResponse]
    total: int = Field(description="Total number of matching activity log records")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of records per page")
    total_pages: int = Field(description="Total number of pages available")

    model_config = ConfigDict(from_attributes=True)
