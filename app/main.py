import os
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.outreach import draft_outreach
from app.agents.research import research_investor
from app.core.db import get_db
from app.matching.ranker import rank_investors_for_founder
from app.models import Founder, Investor, MatchMessage, MatchPipeline
from app.schemas import AgentRequest, MatchResult, MessageCreate, MessageRead, PipelineUpdate

app = FastAPI(title="Paires Core Demo", version="0.5.1")

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "https://paires-core-demo-production.up.railway.app",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

VALID_STAGES = {"matched", "outreach_sent", "replied", "meeting_booked", "not_a_fit"}
VALID_MEETING_TYPES = {"intro", "follow_up", "partner", "other"}


@app.get("/", response_class=HTMLResponse)
async def home():
    with open("app/static/index.html", "r") as f:
        return f.read()


@app.get("/api/founders")
async def list_founders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Founder).order_by(Founder.id))
    founders = result.scalars().all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "company": f.company,
            "stage": f.stage,
            "sector": f.sector,
            "description": f.description,
        }
        for f in founders
    ]


@app.get("/api/founders/{founder_id}/matches", response_model=list[MatchResult])
async def get_matches(founder_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Founder).where(Founder.id == founder_id))
    founder = result.scalar_one_or_none()
    if founder is None or founder.embedding is None:
        raise HTTPException(status_code=404, detail="Founder not found or missing embedding")

    return await rank_investors_for_founder(
        session=db,
        founder_embedding=list(founder.embedding),
        founder_id=founder_id,
        founder_stage=founder.stage,
        founder_sector=founder.sector,
        limit=5,
    )


async def _get_or_create_pipeline(
    db: AsyncSession,
    founder_id: int,
    investor_id: int,
    score: float | None = None,
) -> MatchPipeline:
    pipe = (
        await db.execute(
            select(MatchPipeline).where(
                MatchPipeline.founder_id == founder_id,
                MatchPipeline.investor_id == investor_id,
            )
        )
    ).scalar_one_or_none()
    if pipe is None:
        pipe = MatchPipeline(
            founder_id=founder_id,
            investor_id=investor_id,
            current_stage="matched",
            score_at_match=score,
        )
        db.add(pipe)
        await db.flush()
    return pipe


@app.post("/api/pipeline")
async def update_pipeline(payload: PipelineUpdate, db: AsyncSession = Depends(get_db)):
    if payload.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Use one of: {sorted(VALID_STAGES)}")

    if payload.meeting_type and payload.meeting_type not in VALID_MEETING_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid meeting_type. Use one of: {sorted(VALID_MEETING_TYPES)}",
        )

    founder = (await db.execute(select(Founder).where(Founder.id == payload.founder_id))).scalar_one_or_none()
    investor = (await db.execute(select(Investor).where(Investor.id == payload.investor_id))).scalar_one_or_none()
    if not founder or not investor:
        raise HTTPException(status_code=404, detail="Founder or Investor not found")

    pipe = await _get_or_create_pipeline(db, payload.founder_id, payload.investor_id, payload.score)
    pipe.current_stage = payload.stage

    if payload.reply_summary is not None:
        pipe.last_reply_summary = payload.reply_summary
    if payload.notes is not None:
        pipe.notes = payload.notes
    if payload.score is not None and pipe.score_at_match is None:
        pipe.score_at_match = payload.score

    if payload.stage == "meeting_booked":
        if payload.meeting_at is not None:
            pipe.meeting_at = payload.meeting_at
        if payload.meeting_type is not None:
            pipe.meeting_type = payload.meeting_type
        if payload.meeting_notes is not None:
            pipe.meeting_notes = payload.meeting_notes
        if payload.follow_up_expected is not None:
            pipe.follow_up_expected = payload.follow_up_expected

        when = pipe.meeting_at.strftime("%a %d %b %Y %H:%M") if pipe.meeting_at else "time TBC"
        mtype = (pipe.meeting_type or "intro").replace("_", " ")
        follow = " · Follow-up expected" if pipe.follow_up_expected else ""
        notes = f" · {pipe.meeting_notes}" if pipe.meeting_notes else ""
        body = f"Meeting booked · {mtype} · {when}{follow}{notes}"
        db.add(
            MatchMessage(
                founder_id=payload.founder_id,
                investor_id=payload.investor_id,
                sender="system",
                kind="system",
                body=body,
            )
        )
    elif payload.stage == "not_a_fit":
        pipe.meeting_at = None
        pipe.meeting_type = None
        pipe.meeting_notes = None
        pipe.follow_up_expected = False

    await db.commit()
    await db.refresh(pipe)

    return {
        "status": "ok",
        "founder_id": pipe.founder_id,
        "investor_id": pipe.investor_id,
        "current_stage": pipe.current_stage,
        "last_reply_summary": pipe.last_reply_summary,
        "meeting_at": pipe.meeting_at.isoformat() if pipe.meeting_at else None,
        "meeting_type": pipe.meeting_type,
        "meeting_notes": pipe.meeting_notes,
        "follow_up_expected": pipe.follow_up_expected,
    }


@app.get("/api/thread/{founder_id}/{investor_id}", response_model=list[MessageRead])
async def get_thread(founder_id: int, investor_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MatchMessage)
        .where(
            MatchMessage.founder_id == founder_id,
            MatchMessage.investor_id == investor_id,
        )
        .order_by(MatchMessage.created_at.asc())
    )
    return result.scalars().all()


@app.post("/api/thread", response_model=MessageRead)
async def post_message(payload: MessageCreate, db: AsyncSession = Depends(get_db)):
    if payload.sender not in {"founder", "investor", "system", "agent"}:
        raise HTTPException(status_code=400, detail="Invalid sender")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    founder = (await db.execute(select(Founder).where(Founder.id == payload.founder_id))).scalar_one_or_none()
    investor = (await db.execute(select(Investor).where(Investor.id == payload.investor_id))).scalar_one_or_none()
    if not founder or not investor:
        raise HTTPException(status_code=404, detail="Founder or Investor not found")

    msg = MatchMessage(
        founder_id=payload.founder_id,
        investor_id=payload.investor_id,
        sender=payload.sender,
        kind=payload.kind,
        body=payload.body.strip(),
    )
    db.add(msg)

    pipe = await _get_or_create_pipeline(db, payload.founder_id, payload.investor_id)

    if payload.mark_outreach_sent or payload.kind == "outreach":
        if pipe.current_stage in {"matched", "outreach_sent"}:
            pipe.current_stage = "outreach_sent"
    if payload.sender == "investor" or payload.kind == "reply":
        pipe.current_stage = "replied"
        pipe.last_reply_summary = payload.body.strip()[:500]

    await db.commit()
    await db.refresh(msg)
    return msg


@app.post("/api/research")
async def run_research(payload: AgentRequest, db: AsyncSession = Depends(get_db)):
    founder = (await db.execute(select(Founder).where(Founder.id == payload.founder_id))).scalar_one_or_none()
    investor = (await db.execute(select(Investor).where(Investor.id == payload.investor_id))).scalar_one_or_none()
    if not founder or not investor:
        raise HTTPException(status_code=404, detail="Founder or Investor not found")

    pipe = (
        await db.execute(
            select(MatchPipeline).where(
                MatchPipeline.founder_id == payload.founder_id,
                MatchPipeline.investor_id == payload.investor_id,
            )
        )
    ).scalar_one_or_none()

    thread = (
        await db.execute(
            select(MatchMessage)
            .where(
                MatchMessage.founder_id == payload.founder_id,
                MatchMessage.investor_id == payload.investor_id,
            )
            .order_by(MatchMessage.created_at.desc())
            .limit(8)
        )
    ).scalars().all()
    thread_lines = [f"- [{m.sender}/{m.kind}] {m.body[:300]}" for m in reversed(list(thread))]
    thread_block = "\n".join(thread_lines) if thread_lines else "No messages yet."

    context_extra = f"\nConversation thread:\n{thread_block}"
    if pipe:
        context_extra += f"\nCurrent pipeline stage: {pipe.current_stage}"
        if pipe.last_reply_summary:
            context_extra += f"\nLast reply summary: {pipe.last_reply_summary}"
        if pipe.meeting_at:
            context_extra += f"\nMeeting at: {pipe.meeting_at.isoformat()}"
            context_extra += f"\nMeeting type: {pipe.meeting_type or 'n/a'}"
            context_extra += f"\nFollow-up expected: {bool(pipe.follow_up_expected)}"
            if pipe.meeting_notes:
                context_extra += f"\nMeeting notes: {pipe.meeting_notes}"

    brief = await research_investor(
        investor_name=investor.name,
        firm=investor.firm,
        thesis=investor.thesis,
        founder_context=f"{founder.name} of {founder.company}: {founder.description}{context_extra}",
        sector=founder.sector,
    )
    return {"brief": brief}


@app.post("/api/outreach")
async def run_outreach(payload: AgentRequest, db: AsyncSession = Depends(get_db)):
    founder = (await db.execute(select(Founder).where(Founder.id == payload.founder_id))).scalar_one_or_none()
    investor = (await db.execute(select(Investor).where(Investor.id == payload.investor_id))).scalar_one_or_none()
    if not founder or not investor:
        raise HTTPException(status_code=404, detail="Founder or Investor not found")

    thread = (
        await db.execute(
            select(MatchMessage)
            .where(
                MatchMessage.founder_id == payload.founder_id,
                MatchMessage.investor_id == payload.investor_id,
            )
            .order_by(MatchMessage.created_at.desc())
            .limit(6)
        )
    ).scalars().all()
    thread_ctx = "\n".join(f"[{m.sender}] {m.body[:280]}" for m in reversed(list(thread)))
    extra = f"\nRecent thread:\n{thread_ctx}" if thread_ctx else ""

    email = await draft_outreach(
        investor_name=investor.name,
        firm=investor.firm,
        thesis=investor.thesis,
        founder_name=founder.name,
        company=founder.company,
        description=founder.description + extra,
    )
    return {"email": email}