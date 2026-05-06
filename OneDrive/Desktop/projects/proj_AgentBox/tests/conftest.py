import asyncio
import tempfile
import pytest

from agentbox.api.hitl import HITLQueue
from agentbox.api.ws import WSHub


@pytest.fixture
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def hitl_queue():
    return HITLQueue()


@pytest.fixture
def ws_hub():
    return WSHub()
