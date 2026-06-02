from zoneinfo import ZoneInfo
from datetime import datetime, date

KST = ZoneInfo("Asia/Seoul")


def kst_today() -> date:
    return datetime.now(KST).date()
