from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class QuestionRequest(BaseModel):
    question: str
    user_id: str
    username: str
    channel_id: str
    guild_id: Optional[str] = None
    timestamp: datetime = datetime.now()


class WoWArticle(BaseModel):
    id: str
    title: str
    content: str
    url: str
    published_date: datetime
    summary: Optional[str] = None
    
    class Config:
        frozen = True


class AIResponse(BaseModel):
    content: str
    source_articles: List[str] = []
    confidence: Optional[float] = None
    timestamp: datetime = datetime.now()
    
    class Config:
        frozen = True


class VectorDocument(BaseModel):
    id: str
    content: str
    metadata: dict
    embedding: Optional[List[float]] = None
    
    class Config:
        frozen = True