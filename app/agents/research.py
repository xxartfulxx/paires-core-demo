from app.agents.web_signals import format_signals_for_prompt, gather_online_signals
from app.llm.factory import get_llm_client


async def research_investor(
    investor_name: str,
    firm: str,
    thesis: str,
    founder_context: str,
    sector: str | None = None,
) -> str:
    client = get_llm_client()
    signals = await gather_online_signals(investor_name, firm, sector=sector)
    online_block = format_signals_for_prompt(signals)

    system = """You are the research agent inside an AI fundraising platform (Paires-style).

Write a structured research brief a founder can trust.

You MUST use this exact section layout:

## Internal (what we already hold)
- Stated thesis / CRM-style facts from our database
- Relationship / thread state if provided
- Do not pretend internal data came from the web

## Web findings (live)
- What the web search actually turned up
- Recent activity, fund positioning, market/sector movement
- Cite with source titles or URLs when possible
- If web evidence is thin or noisy, say so clearly

## Fit & timing
- Why this investor may or may not fit this founder now
- Any market shift that changes the match

## Talking points
- 3 concrete points for outreach or a call

## Risks / unknowns
- Gaps, contradictions, or things to verify

Rules:
- Never invent portfolio companies, check sizes, or quotes not supported by inputs.
- Separate internal vs web clearly so a human can audit the brief.
- Be concise and practical, not promotional.
"""

    user = f"""Investor: {investor_name}
Firm: {firm}
Internal stated thesis: {thesis}

Founder + relationship context (internal):
{founder_context}

{online_block}

Produce the research brief now."""

    return await client.complete(system=system, user=user, temperature=0.25)