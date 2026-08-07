import asyncio

from app.core.db import Base, engine
from app.models import Founder, Investor, MatchFeedback  # noqa: F401


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")


if __name__ == "__main__":
    asyncio.run(main())