import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import settings


async def clean_db():
    engine = create_async_engine(str(settings.DATABASE_URL))
    async with engine.begin() as conn:
        # Get all table names
        result = await conn.execute(
            text("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
        """)
        )
        tables = [row[0] for row in result.fetchall()]

        # Don't truncate alembic_version, so we keep the schema state and tables intact
        tables = [t for t in tables if t != "alembic_version"]

        if not tables:
            print("No tables found to clean.")
            return

        tables_str = ", ".join([f'"{t}"' for t in tables])
        print(f"Truncating tables to clear all data (but keeping tables): {tables_str}")

        # TRUNCATE CASCADE deletes all data in the tables and their dependent tables, leaving the tables themselves empty.
        # RESTART IDENTITY resets auto-increment sequences so IDs start from 1 again.
        await conn.execute(
            text(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;")
        )
        print("Database data wiped successfully! All tables are now empty.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(clean_db())
