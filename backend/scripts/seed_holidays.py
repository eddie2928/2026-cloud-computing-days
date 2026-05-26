"""
한국 공휴일 및 기념일 시드 스크립트.
실행: cd backend && python -m scripts.seed_holidays
"""

import asyncio
from datetime import date

import holidays as holidays_lib
from sqlalchemy import text

from app.db import get_session_factory

SEED_YEARS = range(2024, 2029)

# 법정 공휴일이 아닌 기념일 (월, 일) → is_holiday=False
EXTRA_ANNIVERSARIES = [
    (2, 14, "발렌타인데이"),
    (3, 14, "화이트데이"),
    (4, 5, "식목일"),
    (5, 8, "어버이날"),
    (5, 15, "스승의날"),
    (11, 11, "빼빼로데이"),
]


def build_rows() -> list[dict]:
    rows: dict[date, dict] = {}

    kr = holidays_lib.country_holidays("KR", years=list(SEED_YEARS))
    for d, name in kr.items():
        rows[d] = {"date": d, "name": name, "is_holiday": True}

    for year in SEED_YEARS:
        for month, day, name in EXTRA_ANNIVERSARIES:
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d not in rows:
                rows[d] = {"date": d, "name": name, "is_holiday": False}

    return list(rows.values())


async def seed() -> None:
    factory = get_session_factory()
    rows = build_rows()

    async with factory() as session:
        for row in rows:
            await session.execute(
                text(
                    "INSERT INTO holidays (date, name, is_holiday) "
                    "VALUES (:date, :name, :is_holiday) "
                    "ON CONFLICT (date) DO UPDATE "
                    "SET name = EXCLUDED.name, is_holiday = EXCLUDED.is_holiday"
                ),
                row,
            )
        await session.commit()

    print(f"Seeded {len(rows)} holiday/anniversary rows.")


if __name__ == "__main__":
    asyncio.run(seed())
