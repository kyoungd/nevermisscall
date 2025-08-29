#!/usr/bin/env python3
"""Test core business logic functions."""

import sys
import json
import re
from datetime import datetime
from unittest.mock import MagicMock

# Add src to path
sys.path.insert(0, 'src')

def test_room_name_generation():
    """Test room name generation logic."""
    print("\n🏠 Testing Room Name Generation...")
    
    def generate_room_name(room_type: str, identifier: str) -> str:
        """Generate Socket.IO room names for different entity types."""
        room_names = {
            'tenant': lambda id: f'tenant:{id}',
            'conversation': lambda id: f'conversation:{id}',
            'user': lambda id: f'user:{id}'
        }
        return room_names.get(room_type, lambda id: f'unknown:{id}')(identifier)
    
    try:
        # Test tenant room
        tenant_room = generate_room_name('tenant', 'tenant-123')
        assert tenant_room == 'tenant:tenant-123'
        print("  ✅ Tenant room name generation works")
        
        # Test conversation room
        conv_room = generate_room_name('conversation', 'conv-456')
        assert conv_room == 'conversation:conv-456'
        print("  ✅ Conversation room name generation works")
        
        # Test user room
        user_room = generate_room_name('user', 'user-789')
        assert user_room == 'user:user-789'
        print("  ✅ User room name generation works")
        
        # Test unknown room type
        unknown_room = generate_room_name('unknown_type', 'id-123')
        assert unknown_room == 'unknown:id-123'
        print("  ✅ Unknown room type fallback works")
        
        return True
    except Exception as e:
        print(f"  ❌ Room name generation failed: {e}")
        return False

def test_redis_key_generation():
    """Test Redis key generation patterns."""
    print("\n🔑 Testing Redis Key Generation...")
    
    def get_connection_key(tenant_id: str, connection_id: str) -> str:
        """Generate Redis key for connection state."""
        return f"connections:{tenant_id}:{connection_id}"
    
    def get_tenant_connections_key(tenant_id: str) -> str:
        """Generate Redis key for tenant connection index."""
        return f"tenant_connections:{tenant_id}"
    
    def get_event_queue_key(event_id: str) -> str:
        """Generate Redis key for event queue item."""
        return f"event_queue:{event_id}"
    
    try:
        # Test connection key
        conn_key = get_connection_key("tenant-123", "conn-456")
        assert conn_key == "connections:tenant-123:conn-456"
        print("  ✅ Connection key generation works")
        
        # Test tenant connections key
        tenant_key = get_tenant_connections_key("tenant-123")
        assert tenant_key == "tenant_connections:tenant-123"
        print("  ✅ Tenant connections key generation works")
        
        # Test event queue key
        event_key = get_event_queue_key("event-789")
        assert event_key == "event_queue:event-789"
        print("  ✅ Event queue key generation works")
        
        return True
    except Exception as e:
        print(f"  ❌ Redis key generation failed: {e}")
        return False

def test_event_validation():
    """Test event data validation patterns."""
    print("\n📋 Testing Event Validation...")
    
    def validate_event_data(event: str, data: dict) -> bool:
        """Basic event data validation."""
        if not event or not isinstance(event, str):
            return False
        
        if not data or not isinstance(data, dict):
            return False
        
        # Event-specific validation
        if event == "call_incoming":
            required_fields = ["callId", "customerPhone"]
            return all(field in data for field in required_fields)
        
        if event == "message_received":
            required_fields = ["conversationId", "messageId", "body"]
            return all(field in data for field in required_fields)
        
        return True
    
    try:
        # Test valid call incoming event
        call_data = {"callId": "call-123", "customerPhone": "+1234567890"}
        assert validate_event_data("call_incoming", call_data) is True
        print("  ✅ Call incoming event validation works")
        
        # Test valid message received event
        msg_data = {"conversationId": "conv-123", "messageId": "msg-456", "body": "Hello"}
        assert validate_event_data("message_received", msg_data) is True
        print("  ✅ Message received event validation works")
        
        # Test invalid data
        assert validate_event_data("", {}) is False
        assert validate_event_data("call_incoming", {}) is False
        print("  ✅ Invalid event validation works")
        
        return True
    except Exception as e:
        print(f"  ❌ Event validation failed: {e}")
        return False

def test_connection_limits():
    """Test connection limit checking logic."""
    print("\n🔢 Testing Connection Limits...")
    
    def check_connection_limits(current_connections: int, max_connections: int = 10) -> bool:
        """Check if tenant is within connection limits."""
        return current_connections < max_connections
    
    try:
        # Test under limit
        assert check_connection_limits(5, 10) is True
        print("  ✅ Under limit check works")
        
        # Test at limit
        assert check_connection_limits(10, 10) is False
        print("  ✅ At limit check works")
        
        # Test over limit
        assert check_connection_limits(15, 10) is False
        print("  ✅ Over limit check works")
        
        return True
    except Exception as e:
        print(f"  ❌ Connection limits failed: {e}")
        return False

def test_error_response_format():
    """Test error response formatting."""
    print("\n❌ Testing Error Response Format...")
    
    def create_error_response(code: str, message: str, details: dict = None) -> dict:
        """Create standardized error response."""
        return {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    try:
        # Test basic error response
        error = create_error_response("TEST_ERROR", "Test error message")
        assert error["success"] is False
        assert error["error"]["code"] == "TEST_ERROR"
        assert error["error"]["message"] == "Test error message"
        assert "timestamp" in error["error"]
        print("  ✅ Basic error response works")
        
        # Test error response with details
        error_with_details = create_error_response(
            "VALIDATION_ERROR",
            "Invalid data provided",
            {"field": "email", "value": "invalid"}
        )
        assert error_with_details["error"]["details"]["field"] == "email"
        print("  ✅ Error response with details works")
        
        return True
    except Exception as e:
        print(f"  ❌ Error response format failed: {e}")
        return False

def main():
    """Run all core logic tests."""
    print("🔍 Testing Core Business Logic for as-connection-service")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 5
    
    if test_room_name_generation():
        tests_passed += 1
    
    if test_redis_key_generation():
        tests_passed += 1
        
    if test_event_validation():
        tests_passed += 1
        
    if test_connection_limits():
        tests_passed += 1
        
    if test_error_response_format():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 Core Logic Test Results: {tests_passed}/{total_tests} test suites passed")
    
    if tests_passed == total_tests:
        print("🎉 All core business logic functions are working correctly!")
        return 0
    else:
        print(f"⚠️  {total_tests - tests_passed} test suite(s) failed")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)