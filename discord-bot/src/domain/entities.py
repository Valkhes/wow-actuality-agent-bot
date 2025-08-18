from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WoWQuestion(BaseModel):
    content: str
    user_id: str
    username: str
    channel_id: str
    guild_id: Optional[str] = None
    timestamp: datetime = datetime.now()
    
    class Config:
        frozen = True


class WoWResponse(BaseModel):
    content: str
    timestamp: datetime = datetime.now()
    source_articles: Optional[list[str]] = None
    confidence: Optional[float] = None
    
    class Config:
        frozen = True


class BotUser(BaseModel):
    id: str
    username: str
    discriminator: str
    avatar_url: Optional[str] = None
    
    class Config:
        frozen = True