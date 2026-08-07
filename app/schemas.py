from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FounderCreate(BaseModel):
    name: str
    company: str
    stage: str
    sector: str
    description: str
    meta: dict = Field(default_factory=dict)


class FounderRead(FounderCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class InvestorCreate(BaseModel):
    name: str
    firm: str
    thesis: str
    preferred_stages: list[str] = Field(default_factory=list)
    preferred_sectors: list[str] = Field(default_factory=list)
    check_size_min: Optional[float] = None
    check_size_max: Optional[float] = None
    meta: dict = Field(default_factory=dict)


class InvestorRead(InvestorCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class MatchResult(BaseModel):
    investor_id: int
    investor_name: str
    firm: str
    score: float
    thesis: str
    current_stage: str = "matched"
    last_reply_summary: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    meeting_at: Optional[datetime] = None
    meeting_type: Optional[str] = None
    follow_up_expected: Optional[bool] = None


class PipelineUpdate(BaseModel):
    founder_id: int
    investor_id: int
    stage: str
    reply_summary: Optional[str] = None
    notes: Optional[str] = None
    score: Optional[float] = None
    meeting_at: Optional[datetime] = None
    meeting_type: Optional[str] = None
    meeting_notes: Optional[str] = None
    follow_up_expected: Optional[bool] = None


class AgentRequest(BaseModel):
    founder_id: int
    investor_id: int


class MessageCreate(BaseModel):
    founder_id: int
    investor_id: int
    sender: str
    kind: str = "note"
    body: str
    mark_outreach_sent: bool = False


class MessageRead(BaseModel):
    id: int
    founder_id: int
    investor_id: int
    sender: str
    kind: str
    body: str
    created_at: datetime

    class Config:
        from_attributes = True