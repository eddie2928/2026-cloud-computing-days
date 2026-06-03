import os
import urllib.request

from mcp.server.fastmcp import FastMCP

from mcp_server.db import AsyncSessionLocal
import mcp_server.tools as t


def _allowed_hosts() -> list[str]:
    hosts = ["localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"]
    try:
        # EC2 instance metadata: get private IP for VPC-internal callers
        ip = urllib.request.urlopen(
            "http://169.254.169.254/latest/meta-data/local-ipv4", timeout=1
        ).read().decode().strip()
        hosts += [ip, f"{ip}:*"]
    except Exception:
        pass
    return hosts


mcp = FastMCP("qna-diary", stateless_http=True, json_response=True, allowed_hosts=_allowed_hosts())


def _db_err(exc: Exception) -> dict:
    return {"status": "error", "code": "DB_ERROR", "message": type(exc).__name__}


@mcp.tool()
async def list_users() -> dict:
    """
    Returns a list of all registered users. Use this tool first when you need to
    discover which users exist in the system before querying diary or schedule data.
    Each result includes user_id (use this as input for other tools), display_name,
    and created_at. Profile fields (nickname, gender, age, occupation, hobbies,
    interests) are nested under a 'profile' key and are null if the user has not
    completed profile setup.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await t.list_users(session)
    except Exception as exc:
        return _db_err(exc)


@mcp.tool()
async def get_user_info(user_id: int) -> dict:
    """
    Returns profile information for a single user identified by user_id.
    Use this when you already know the user_id and need their personal background
    (age, gender, occupation, hobbies, interests) to contextualize their diary
    entries. The 'profile' field is null if the user has not completed profile setup;
    the user record itself (display_name, created_at) is still returned.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await t.get_user_info(session, user_id)
    except Exception as exc:
        return _db_err(exc)


@mcp.tool()
async def list_diaries(user_id: int, date_from: str, date_to: str) -> dict:
    """
    Returns a summary list of diary entries for a user within a date range.
    Use this to get an overview of a user's diary history — how many entries exist,
    what emotions were recorded on which dates, and the one-sentence summary of
    each day. Does NOT include the full diary body text or QnA conversation;
    use get_diary_session for that. date_from and date_to are inclusive, in
    YYYY-MM-DD format. Entries are returned sorted by diary_date ascending.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await t.list_diaries(session, user_id, date_from, date_to)
    except Exception as exc:
        return _db_err(exc)


@mcp.tool()
async def get_diary_session(user_id: int, date: str) -> dict:
    """
    Returns the complete record for a single diary date: the full QnA conversation
    that led to the diary (each question the AI asked and the user's answer, in
    sequence order), plus the final diary entry (full body text, summary sentence,
    and emotion label). Emotion is one of: happy, sad, angry, neutral, bored.
    Use this when you need to understand the context behind a diary entry — what
    the user actually said during the session, not just the AI-generated summary.
    Returns null if no diary session exists for that date. If the session exists but
    is still in_progress (diary not yet finalized), the 'diary' field will be null.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await t.get_diary_session(session, user_id, date)
    except Exception as exc:
        return _db_err(exc)


@mcp.tool()
async def get_emotion_trend(user_id: int, date_from: str, date_to: str) -> dict:
    """
    Returns the emotion label recorded for each diary entry within a date range,
    sorted by date ascending. Use this to analyze emotional patterns over time —
    for example, to find streaks of the same emotion, detect mood changes, or
    compare emotional states across different periods. Only dates that have a
    completed diary entry are included; missing dates mean no diary was written.
    Emotion values are: happy, sad, angry, neutral, bored.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await t.get_emotion_trend(session, user_id, date_from, date_to)
    except Exception as exc:
        return _db_err(exc)


@mcp.tool()
async def get_user_schedules(user_id: int, date_from: str | None = None,
                              date_to: str | None = None) -> dict:
    """
    Returns the user's personal schedule entries (situations/events) within a date
    range. Each schedule has a period_start and period_end (the event spans those
    dates) and a situation description (free text written by the user). Use this
    to understand what was happening in the user's life during a period — useful
    for correlating life events with diary content or emotional changes.
    date_from and date_to filter by overlap with the schedule's period
    (i.e. schedules that were active at any point within the range are included).
    Both date parameters are optional; omitting both returns all schedules.
    """
    try:
        async with AsyncSessionLocal() as session:
            return await t.get_user_schedules(session, user_id, date_from, date_to)
    except Exception as exc:
        return _db_err(exc)


# ASGI app for uvicorn
app = mcp.streamable_http_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("MCP_PORT", "8080")))
