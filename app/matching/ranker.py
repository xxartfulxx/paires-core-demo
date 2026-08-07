from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Investor, MatchPipeline
from app.schemas import MatchResult

STAGE_BOOST = {
    "matched": 0.0,
    "outreach_sent": 0.04,
    "replied": 0.10,
    "meeting_booked": 0.18,
    "not_a_fit": -0.25,
}


def _build_reasons(
    base_score: float,
    investor: Investor,
    founder_stage: str | None,
    founder_sector: str | None,
    current_stage: str,
    hist_signal: float,
    meeting_at=None,
    follow_up_expected: bool | None = None,
) -> list[str]:
    reasons = []

    if base_score >= 0.55:
        reasons.append("Strong thesis overlap")
    elif base_score >= 0.40:
        reasons.append("Moderate thesis overlap")
    else:
        reasons.append("Partial thesis overlap")

    if founder_stage and investor.preferred_stages and founder_stage in investor.preferred_stages:
        reasons.append(f"Stage fit ({founder_stage})")

    if founder_sector and investor.preferred_sectors and founder_sector in investor.preferred_sectors:
        reasons.append(f"Sector fit ({founder_sector})")

    if current_stage == "matched":
        reasons.append("No prior relationship yet")
    elif current_stage == "outreach_sent":
        reasons.append("Outreach already sent")
    elif current_stage == "replied":
        reasons.append("Investor has replied")
    elif current_stage == "meeting_booked":
        if meeting_at is not None:
            reasons.append(f"Meeting booked ({meeting_at.strftime('%d %b %Y %H:%M')})")
        else:
            reasons.append("Meeting booked")
        if follow_up_expected:
            reasons.append("Follow-up expected")
    elif current_stage == "not_a_fit":
        reasons.append("Previously marked not a fit")

    if hist_signal > 0.04:
        reasons.append("Investor tends to engage after outreach")
    elif hist_signal < -0.04:
        reasons.append("Investor often goes cold")

    return reasons


async def _investor_conversion_signal(session: AsyncSession, investor_ids: list[int]) -> dict[int, float]:
    if not investor_ids:
        return {}

    stmt = (
        select(
            MatchPipeline.investor_id,
            MatchPipeline.current_stage,
            func.count().label("cnt"),
        )
        .where(MatchPipeline.investor_id.in_(investor_ids))
        .group_by(MatchPipeline.investor_id, MatchPipeline.current_stage)
    )
    rows = (await session.execute(stmt)).all()

    stats: dict[int, dict[str, int]] = {}
    for inv_id, stage, cnt in rows:
        stats.setdefault(inv_id, {})
        stats[inv_id][stage] = cnt

    signals: dict[int, float] = {}
    for inv_id, stage_counts in stats.items():
        total = sum(stage_counts.values()) or 1
        positive = stage_counts.get("replied", 0) + stage_counts.get("meeting_booked", 0) * 2
        negative = stage_counts.get("not_a_fit", 0) * 1.5
        signals[inv_id] = max(-0.12, min(0.12, (positive - negative) / total * 0.15))
    return signals


async def rank_investors_for_founder(
    session: AsyncSession,
    founder_embedding: list[float],
    founder_id: int | None = None,
    founder_stage: str | None = None,
    founder_sector: str | None = None,
    limit: int = 10,
) -> list[MatchResult]:
    stmt = (
        select(
            Investor,
            (Investor.embedding.cosine_distance(founder_embedding)).label("distance"),
        )
        .where(Investor.embedding.is_not(None))
        .order_by("distance")
        .limit(limit * 4)
    )

    if founder_stage:
        stmt = stmt.where(Investor.preferred_stages.contains([founder_stage]))
    if founder_sector:
        stmt = stmt.where(Investor.preferred_sectors.contains([founder_sector]))

    result = await session.execute(stmt)
    rows = result.all()
    investor_ids = [inv.id for inv, _ in rows]

    pipeline_map: dict[int, MatchPipeline] = {}
    if founder_id is not None and investor_ids:
        pipe_rows = (
            await session.execute(
                select(MatchPipeline).where(
                    MatchPipeline.founder_id == founder_id,
                    MatchPipeline.investor_id.in_(investor_ids),
                )
            )
        ).scalars().all()
        pipeline_map = {p.investor_id: p for p in pipe_rows}

    hist_signals = await _investor_conversion_signal(session, investor_ids)

    scored = []
    for investor, distance in rows:
        base = 1.0 - float(distance)
        pipe = pipeline_map.get(investor.id)
        current_stage = pipe.current_stage if pipe else "matched"
        stage_boost = STAGE_BOOST.get(current_stage, 0.0)
        hist_boost = hist_signals.get(investor.id, 0.0)
        final = base + stage_boost + hist_boost

        reasons = _build_reasons(
            base_score=base,
            investor=investor,
            founder_stage=founder_stage,
            founder_sector=founder_sector,
            current_stage=current_stage,
            hist_signal=hist_boost,
            meeting_at=pipe.meeting_at if pipe else None,
            follow_up_expected=pipe.follow_up_expected if pipe else None,
        )

        scored.append((investor, final, current_stage, pipe, reasons))

    scored.sort(key=lambda x: x[1], reverse=True)
    scored = scored[:limit]

    matches: list[MatchResult] = []
    for inv, score, current_stage, pipe, reasons in scored:
        matches.append(
            MatchResult(
                investor_id=inv.id,
                investor_name=inv.name,
                firm=inv.firm,
                score=round(max(0.0, min(1.0, score)), 4),
                thesis=inv.thesis,
                current_stage=current_stage,
                last_reply_summary=pipe.last_reply_summary if pipe else None,
                reasons=reasons,
                meeting_at=pipe.meeting_at if pipe else None,
                meeting_type=pipe.meeting_type if pipe else None,
                follow_up_expected=pipe.follow_up_expected if pipe else None,
            )
        )
    return matches