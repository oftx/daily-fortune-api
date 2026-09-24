"""初始化 config 表里的 registration_status 记录。"""
import asyncio
from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.db_models import AppConfig


async def seed():
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(AppConfig).where(AppConfig.key == "registration_status")
        )).scalar_one_or_none()
        if existing:
            print("registration_status 已存在，跳过。")
            return
        db.add(AppConfig(key="registration_status", value=True))
        await db.commit()
        print("已创建 registration_status = True")


if __name__ == "__main__":
    asyncio.run(seed())
