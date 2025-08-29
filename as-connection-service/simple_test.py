#!/usr/bin/env python3
"""Simple test runner for core functionality."""

import sys
import unittest
from datetime import datetime
from pydantic import ValidationError

# Add src to path
sys.path.insert(0, 'src')

# Test the data models directly
try:
    from as_connection_service.models.connection import ConnectionState, EventQueueItem
    from as_connection_service.models.events import (
        WebSocketEvent,
        BroadcastRequest,
        AuthenticationData,
        TakeoverConversationData,
        SendMessageData,
        UpdateLeadStatusData
    )
    print("✅ Successfully imported data models")
except Exception as e:
    print(f"❌ Failed to import data models: {e}")
    sys.exit(1)

# Test the configuration
try:
    from as_connection_service.config.settings import Settings
    print("✅ Successfully imported settings")
except Exception as e:
    print(f"❌ Failed to import settings: {e}")
    sys.exit(1)

def test_core_models():
    """Test core data model functionality."""
    print("\n🧪 Testing Core Models...")
    
    # Test ConnectionState
    try:
        now = datetime.utcnow()
        connection = ConnectionState(
            connection_id="test-conn",
            socket_id="test-socket", 
            user_id="test-user",
            tenant_id="test-tenant",
            connected_at=now,
            last_activity=now,
            subscribed_conversations=[],
            subscribed_events=[],
            is_active=True,
            redis_key="test:key",
            ttl=3600
        )
        assert connection.connection_id == "test-conn"
        assert connection.is_active is True
        print("  ✅ ConnectionState model works")
    except Exception as e:
        print(f"  ❌ ConnectionState failed: {e}")
        return False
    
    # Test WebSocketEvent
    try:
        event = WebSocketEvent(
            event="test_event",
            data={"test": "data"}
        )
        assert event.event == "test_event"
        assert event.data["test"] == "data"
        assert event.timestamp is not None
        print("  ✅ WebSocketEvent model works")
    except Exception as e:
        print(f"  ❌ WebSocketEvent failed: {e}")
        return False
    
    # Test BroadcastRequest
    try:
        request = BroadcastRequest(
            event="broadcast_test",
            data={"message": "test"},
            tenant_id="test-tenant"
        )
        assert request.event == "broadcast_test"
        assert request.tenant_id == "test-tenant"
        print("  ✅ BroadcastRequest model works")
    except Exception as e:
        print(f"  ❌ BroadcastRequest failed: {e}")
        return False
    
    # Test validation - missing required field
    try:
        TakeoverConversationData(conversation_id="conv-123")  # Missing message field
        print("  ❌ Validation should have failed for missing message field")
        return False
    except (ValidationError, TypeError):
        print("  ✅ Validation works correctly")
    except Exception as e:
        print(f"  ❌ Unexpected validation error: {e}")
        return False
    
    return True

def test_configuration():
    """Test configuration functionality."""
    print("\n⚙️  Testing Configuration...")
    
    try:
        # Test default settings
        settings = Settings()
        assert settings.service_name == "as-connection-service"
        assert settings.port == 3105
        assert isinstance(settings.cors_origins, list)
        print("  ✅ Default settings work")
        
        # Test CORS parsing
        test_settings = Settings(socketio_cors_origin="http://localhost:3000,https://app.test.com")
        origins = test_settings.cors_origins
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        print("  ✅ CORS origins parsing works")
        
        # Test transports parsing
        transports = test_settings.transports
        assert isinstance(transports, list)
        assert len(transports) > 0
        print("  ✅ Transports parsing works")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")
        return False

def test_business_logic_validation():
    """Test core business logic validation."""
    print("\n📋 Testing Business Logic...")
    
    try:
        # Test event data validation
        takeover_data = TakeoverConversationData(
            conversation_id="conv-123",
            message="Taking over conversation"
        )
        assert takeover_data.conversation_id == "conv-123"
        print("  ✅ Takeover conversation data validation works")
        
        # Test message data validation  
        message_data = SendMessageData(
            conversation_id="conv-123",
            message="Customer service response"
        )
        assert message_data.message == "Customer service response"
        print("  ✅ Send message data validation works")
        
        # Test lead status validation
        lead_data = UpdateLeadStatusData(
            lead_id="lead-123",
            status="qualified",
            notes="Ready for appointment"
        )
        assert lead_data.status == "qualified"
        assert lead_data.notes == "Ready for appointment"
        print("  ✅ Lead status data validation works")
        
        # Test without optional notes
        lead_data_no_notes = UpdateLeadStatusData(
            lead_id="lead-123", 
            status="qualified"
        )
        assert lead_data_no_notes.notes is None
        print("  ✅ Optional fields work correctly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Business logic validation failed: {e}")
        return False

def main():
    """Run all core tests."""
    print("🚀 Running Core Function Tests for as-connection-service")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 3
    
    if test_core_models():
        tests_passed += 1
    
    if test_configuration():
        tests_passed += 1
        
    if test_business_logic_validation():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{total_tests} test suites passed")
    
    if tests_passed == total_tests:
        print("🎉 All core functions are working correctly!")
        return 0
    else:
        print(f"⚠️  {total_tests - tests_passed} test suite(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)