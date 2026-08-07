from app.llm.factory import get_llm_client


async def draft_outreach(
    investor_name: str,
    firm: str,
    thesis: str,
    founder_name: str,
    company: str,
    description: str,
) -> str:
    client = get_llm_client()

    system = """You are an expert at writing warm, concise investor outreach emails.
Write a short, personalized outreach email (under 150 words) that feels human and specific.
Do not be salesy. Focus on relevance and a clear soft ask for a short call.
Return only the email body (no subject line)."""

    user = f"""Investor: {investor_name} ({firm})
Their thesis: {thesis}

Founder: {founder_name}
Company: {company}
What they do: {description}

Write the outreach email."""

    return await client.complete(system=system, user=user)