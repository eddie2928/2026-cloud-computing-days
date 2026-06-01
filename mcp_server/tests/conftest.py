from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _dt(year=2026, month=1, day=1):
    return datetime(year, month, day, tzinfo=timezone.utc)


def make_profile(nickname="Nick", gender="male", age=25, occupation="dev",
                 hobbies=None, interests=None):
    p = MagicMock()
    p.nickname = nickname
    p.gender = gender
    p.age = age
    p.occupation = occupation
    p.hobbies = hobbies or []
    p.interests = interests or []
    return p


def make_user(id=1, display_name="Test User", profile=None, created_at=None):
    u = MagicMock()
    u.id = id
    u.display_name = display_name
    u.created_at = created_at or _dt()
    u.profile = profile
    return u


@pytest.fixture
def session():
    s = AsyncMock()
    return s
