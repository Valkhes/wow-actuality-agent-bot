"""
Pydantic models for LiteLLM Gateway
Data models and validation schemas
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")


class ChatCompletionRequest(BaseModel):
    model: str = Field(default="gemini/gemini-2.0-flash-exp", description="Model to use")
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=1000, gt=0)
    stream: Optional[bool] = Field(default=False)


class SecurityAlert(BaseModel):
    level: str
    message: str
    timestamp: datetime
    request_id: str