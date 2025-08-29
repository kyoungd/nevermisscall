"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database():
    """Mock database query function."""
    return AsyncMock()


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID for testing."""
    return uuid4()


@pytest.fixture
def sample_call_id():
    """Sample call ID for testing."""
    return uuid4()


@pytest.fixture
def sample_conversation_id():
    """Sample conversation ID for testing."""
    return uuid4()


@pytest.fixture
def sample_customer_phone():
    """Sample customer phone number."""
    return "+12125551234"


@pytest.fixture
def sample_business_phone():
    """Sample business phone number."""
    return "+13105551234"


@pytest.fixture
def mock_service_client():
    """Mock service client for external API calls."""
    client = MagicMock()
    client.send_sms_via_twilio_server = AsyncMock()
    client.process_ai_conversation = AsyncMock()
    client.validate_tenant_and_service_area = AsyncMock()
    client.broadcast_realtime_event = AsyncMock()
    return client