"""建表脚本。首次启动时执行一次：python init_db.py"""
import asyncio
from app.db import Base, engine
from app.models import db_models  # noqa: F401


async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("表已创建。")


if __name__ == "__main__":
    asyncio.run(init())
