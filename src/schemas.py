from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID

class GenerateRequest(BaseModel):
    event_type: str = Field(..., description="api_call or ai_token")
    quantity: int = Field(..., gt=0)
    cached_input_tokens: Optional[int] = 0
    reasoning_tokens: Optional[int] = 0

class GenerateResponse(BaseModel):
    status: str
    tenant_id: UUID
    event_id: UUID
    message: str
    idempotent_replay: bool = False

class UsageRequest(BaseModel):
    event_type: str = Field(..., example="api_call")
    quantity: int = Field(..., gt=0, example=100)

class UsageResponse(BaseModel):
    status: str
    tenant_id: str
    event_id: str
    message: str
    idempotent_replay: bool