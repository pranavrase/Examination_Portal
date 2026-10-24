from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class SecurityEventResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    event_type: str
    severity: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    description: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_json")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedSecurityEventsResponse(BaseModel):
    items: List[SecurityEventResponse]
    total: int = Field(description="Total number of security events matching the query criteria")
    page: int = Field(description="Current page number (1-indexed)")
    page_size: int = Field(description="Page size limit")
    total_pages: int = Field(description="Total pages available")

    model_config = ConfigDict(from_attributes=True)
