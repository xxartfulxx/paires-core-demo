import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.matching.embeddings import embed_text
from app.models import Founder, Investor


async def clear_existing(session: AsyncSession) -> None:
    """Optional wipe so re-runs don't duplicate. Comment out if you want to keep history."""
    await session.execute(text("DELETE FROM match_messages"))
    await session.execute(text("DELETE FROM match_pipelines"))
    await session.execute(text("DELETE FROM match_feedback"))
    await session.execute(text("DELETE FROM founders"))
    await session.execute(text("DELETE FROM investors"))
    await session.commit()
    print("Cleared existing seed rows.")


async def seed(session: AsyncSession) -> None:
    founders_data = [
        {
            "name": "Alex Rivera",
            "company": "NovaChip",
            "stage": "seed",
            "sector": "Semiconductors",
            "description": (
                "Building next-generation AI accelerators for edge devices. "
                "Strong team from Apple and NVIDIA. Raising $4M seed."
            ),
        },
        {
            "name": "Priya Shah",
            "company": "LedgerFlow",
            "stage": "series-a",
            "sector": "Fintech",
            "description": (
                "AI-powered treasury and cash-flow management for mid-market companies. "
                "$1.2M ARR, growing 18% MoM. Raising Series A."
            ),
        },
        {
            "name": "Marcus Chen",
            "company": "GridSense",
            "stage": "seed",
            "sector": "Climate",
            "description": (
                "Software + sensors for grid-scale battery optimization and demand response. "
                "Pilots with two utilities. Raising $3.5M seed."
            ),
        },
        {
            "name": "Sofia Alvarez",
            "company": "ClinicLoop",
            "stage": "series-a",
            "sector": "Health",
            "description": (
                "Workflow automation for outpatient clinics: scheduling, prior auth, billing follow-up. "
                "40 clinics live. Raising Series A to expand sales."
            ),
        },
        {
            "name": "Jonah Park",
            "company": "ForgeCAD",
            "stage": "seed",
            "sector": "Manufacturing",
            "description": (
                "AI design assistant for mechanical engineers that turns sketches into manufacturable CAD. "
                "Early revenue from mid-size manufacturers. Raising seed."
            ),
        },
    ]

    for data in founders_data:
        emb = await embed_text(data["description"])
        session.add(Founder(**data, embedding=emb))
        print(f"  founder: {data['name']} ({data['company']})")

    investors_data = [
        {
            "name": "Jordan Lee",
            "firm": "Horizon Ventures",
            "thesis": (
                "We invest in deep tech and frontier hardware, especially semiconductors "
                "and AI infrastructure at seed and Series A."
            ),
            "preferred_stages": ["seed", "series-a"],
            "preferred_sectors": ["Semiconductors", "AI", "Hardware"],
            "check_size_min": 1_000_000,
            "check_size_max": 5_000_000,
        },
        {
            "name": "Samira Khan",
            "firm": "Atlas Capital",
            "thesis": (
                "B2B SaaS and fintech with clear path to $10M ARR. We like capital-efficient "
                "founders and strong unit economics."
            ),
            "preferred_stages": ["seed", "series-a", "series-b"],
            "preferred_sectors": ["Fintech", "SaaS", "Enterprise Software"],
            "check_size_min": 2_000_000,
            "check_size_max": 8_000_000,
        },
        {
            "name": "Marcus Bell",
            "firm": "Pioneer Family Office",
            "thesis": (
                "Long-term capital for category-defining companies in health, climate, "
                "and advanced manufacturing."
            ),
            "preferred_stages": ["series-a", "series-b"],
            "preferred_sectors": ["Health", "Climate", "Manufacturing"],
            "check_size_min": 3_000_000,
            "check_size_max": 15_000_000,
        },
        {
            "name": "Elena Vogt",
            "firm": "Northwind Climate",
            "thesis": (
                "Climate tech with measurable emissions impact. Grid software, storage, "
                "and industrial efficiency at seed and Series A."
            ),
            "preferred_stages": ["seed", "series-a"],
            "preferred_sectors": ["Climate", "Energy", "Hardware"],
            "check_size_min": 500_000,
            "check_size_max": 4_000_000,
        },
        {
            "name": "David Okonkwo",
            "firm": "Beacon Health Partners",
            "thesis": (
                "Healthcare IT and workflow tools that reduce admin burden for providers. "
                "Series A focus, clinical credibility required."
            ),
            "preferred_stages": ["series-a", "series-b"],
            "preferred_sectors": ["Health", "SaaS", "Enterprise Software"],
            "check_size_min": 2_500_000,
            "check_size_max": 10_000_000,
        },
        {
            "name": "Hannah Brooks",
            "firm": "Precision Industrial",
            "thesis": (
                "Software and AI for modern manufacturing floors. CAD, MES, quality, and "
                "supply-chain tools from seed through Series A."
            ),
            "preferred_stages": ["seed", "series-a"],
            "preferred_sectors": ["Manufacturing", "AI", "Enterprise Software"],
            "check_size_min": 750_000,
            "check_size_max": 5_000_000,
        },
        {
            "name": "Tom Rivera",
            "firm": "Cascade Seed",
            "thesis": (
                "Generalist seed fund for technical founders. We write first checks across "
                "deep tech, SaaS, and climate."
            ),
            "preferred_stages": ["seed"],
            "preferred_sectors": ["AI", "SaaS", "Climate", "Hardware", "Fintech"],
            "check_size_min": 250_000,
            "check_size_max": 1_500_000,
        },
        {
            "name": "Aisha Rahman",
            "firm": "Ledger & Co",
            "thesis": (
                "Fintech infrastructure and vertical finance software. Compliance-heavy "
                "products welcome. Seed and Series A."
            ),
            "preferred_stages": ["seed", "series-a"],
            "preferred_sectors": ["Fintech", "SaaS"],
            "check_size_min": 1_000_000,
            "check_size_max": 6_000_000,
        },
    ]

    for data in investors_data:
        emb = await embed_text(data["thesis"])
        session.add(Investor(**data, embedding=emb))
        print(f"  investor: {data['name']} @ {data['firm']}")

    await session.commit()
    print("Seed data inserted successfully.")


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # Wipe old seed so matches are clean and reproducible
        await clear_existing(session)
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())