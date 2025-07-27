from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
from typing import AsyncGenerator
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("A DATABASE_URL környezeti változó nincs beállítva.")

if DATABASE_URL.startswith("sqlite:"):
    async_db_url = DATABASE_URL.replace("://", "+aiosqlite://", 1)
else:
    async_db_url = DATABASE_URL

engine = create_async_engine(
    async_db_url,
    echo=True
)

SessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
