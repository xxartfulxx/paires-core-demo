import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import AsyncSessionLocal
from app.matching.ranker import rank_investors_for_founder
from app.models import Founder


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # Get the first founder (NovaChip)
        result = await session.execute(select(Founder).limit(1))
        founder = result.scalar_one()

        print(f"\nMatching for: {founder.name} ({founder.company})")
        print(f"Stage: {founder.stage} | Sector: {founder.sector}")
        print(f"Description: {founder.description[:120]}...\n")

        matches = await rank_investors_for_founder(
            session=session,
            founder_embedding=founder.embedding,
            limit=5,
            stage=founder.stage,
            sector=founder.sector,
        )

        if not matches:
            print("No matches found.")
            return

        print("Top matches:")
        for i, m in enumerate(matches, 1):
            print(f"{i}. {m.investor_name} @ {m.firm}")
            print(f"   Score: {m.score}")
            print(f"   Thesis: {m.thesis[:100]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main())