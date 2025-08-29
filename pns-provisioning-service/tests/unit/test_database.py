"""Unit tests for database operations."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime

# Add the src directory to Python path
import sys
sys.path.insert(0, '/home/young/Desktop/Code/nvermisscall/nmc/pns-provisioning-service/src')

from pns_provisioning_service.services.database import DatabaseService
from pns_provisioning_service.models.phone_number import PhoneNumber, MessagingService


class TestDatabaseService:
    """Test database service operations."""
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock database pool."""
        pool = AsyncMock()
        connection = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = connection
        pool.acquire.return_value.__aexit__.return_value = None
        return pool, connection
    
    @pytest.fixture
    def database_service(self, mock_pool):
        """Create database service with mocked pool."""
        pool, connection = mock_pool
        service = DatabaseService()
        service.pool = pool
        return service, connection
    
    def test_initialization(self):
        """Test database service initialization."""
        service = DatabaseService()
        assert service.pool is None
        
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful database initialization."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_pool = AsyncMock()
            mock_create_pool.return_value = mock_pool
            
            service = DatabaseService()
            result = await service.initialize()
            
            assert result is True
            assert service.pool == mock_pool
            mock_create_pool.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test failed database initialization."""
        with patch('asyncpg.create_pool') as mock_create_pool:
            mock_create_pool.side_effect = Exception("Connection failed")
            
            service = DatabaseService()
            result = await service.initialize()
            
            assert result is False
            assert service.pool is None
            
    @pytest.mark.asyncio
    async def test_health_check_success(self, database_service):
        """Test successful health check."""
        service, connection = database_service
        connection.fetchval.return_value = 1
        
        result = await service.health_check()
        
        assert result is True
        connection.fetchval.assert_called_once_with("SELECT 1")
        
    @pytest.mark.asyncio
    async def test_health_check_failure(self, database_service):
        """Test failed health check."""
        service, connection = database_service
        connection.fetchval.side_effect = Exception("Connection lost")
        
        result = await service.health_check()
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test database connection closure."""
        mock_pool = AsyncMock()
        service = DatabaseService()
        service.pool = mock_pool
        
        await service.close()
        
        mock_pool.close.assert_called_once()


class TestPhoneNumberOperations:
    """Test phone number database operations."""
    
    @pytest.fixture
    def sample_phone_data(self):
        """Sample phone number data."""
        return {
            'id': uuid4(),
            'tenant_id': uuid4(),
            'phone_number': '+15551234567',
            'phone_number_sid': 'PNxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'messaging_service_sid': 'MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'friendly_name': 'Test Business',
            'status': 'active',
            'capabilities': ['voice', 'sms'],
            'voice_webhook_url': 'https://example.com/voice',
            'sms_webhook_url': 'https://example.com/sms',
            'status_callback_url': 'https://example.com/status',
            'webhooks_configured': True,
            'date_provisioned': datetime.now(),
            'date_released': None,
            'status_reason': None,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    
    @pytest.fixture
    def database_service(self):
        """Create database service with mocked pool."""
        service = DatabaseService()
        pool = AsyncMock()
        connection = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = connection
        pool.acquire.return_value.__aexit__.return_value = None
        service.pool = pool
        return service, connection
    
    @pytest.mark.asyncio
    async def test_store_phone_number(self, database_service, sample_phone_data):
        """Test storing phone number in database."""
        service, connection = database_service
        phone_id = sample_phone_data['id']
        
        # Mock the database response
        connection.fetchrow.return_value = sample_phone_data
        
        phone = PhoneNumber(**sample_phone_data)
        result = await service.store_phone_number(phone)
        
        assert result is not None
        assert result.id == phone_id
        assert result.phone_number == '+15551234567'
        
        # Verify the INSERT query was called
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'INSERT INTO phone_numbers' in call_args[0]
        
    @pytest.mark.asyncio
    async def test_get_phone_number_by_id(self, database_service, sample_phone_data):
        """Test retrieving phone number by ID."""
        service, connection = database_service
        phone_id = sample_phone_data['id']
        
        # Mock database response
        connection.fetchrow.return_value = sample_phone_data
        
        result = await service.get_phone_number_by_id(phone_id)
        
        assert result is not None
        assert result.id == phone_id
        assert result.phone_number == '+15551234567'
        
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'SELECT * FROM phone_numbers WHERE id = $1' in call_args[0]
        assert call_args[1] == phone_id
        
    @pytest.mark.asyncio
    async def test_get_phone_number_by_id_not_found(self, database_service):
        """Test retrieving non-existent phone number by ID."""
        service, connection = database_service
        connection.fetchrow.return_value = None
        
        result = await service.get_phone_number_by_id(uuid4())
        
        assert result is None
        
    @pytest.mark.asyncio
    async def test_get_phone_number_by_number(self, database_service, sample_phone_data):
        """Test retrieving phone number by number string."""
        service, connection = database_service
        phone_number = '+15551234567'
        
        connection.fetchrow.return_value = sample_phone_data
        
        result = await service.get_phone_number_by_number(phone_number)
        
        assert result is not None
        assert result.phone_number == phone_number
        
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'SELECT * FROM phone_numbers WHERE phone_number = $1' in call_args[0]
        assert call_args[1] == phone_number
        
    @pytest.mark.asyncio
    async def test_get_phone_number_by_tenant(self, database_service, sample_phone_data):
        """Test retrieving phone number by tenant ID."""
        service, connection = database_service
        tenant_id = sample_phone_data['tenant_id']
        
        connection.fetchrow.return_value = sample_phone_data
        
        result = await service.get_phone_number_by_tenant(tenant_id)
        
        assert result is not None
        assert result.tenant_id == tenant_id
        
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'SELECT * FROM phone_numbers WHERE tenant_id = $1' in call_args[0]
        assert call_args[1] == tenant_id
        
    @pytest.mark.asyncio
    async def test_update_phone_number_status(self, database_service, sample_phone_data):
        """Test updating phone number status."""
        service, connection = database_service
        phone_id = sample_phone_data['id']
        new_status = 'suspended'
        reason = 'Payment failed'
        
        # Update sample data for response
        updated_data = sample_phone_data.copy()
        updated_data['status'] = new_status
        updated_data['status_reason'] = reason
        connection.fetchrow.return_value = updated_data
        
        result = await service.update_phone_number_status(phone_id, new_status, reason)
        
        assert result is not None
        assert result.status == new_status
        assert result.status_reason == reason
        
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'UPDATE phone_numbers SET' in call_args[0]
        assert 'WHERE id = $3' in call_args[0]
        
    @pytest.mark.asyncio
    async def test_tenant_has_phone_number_true(self, database_service):
        """Test tenant has existing phone number."""
        service, connection = database_service
        tenant_id = uuid4()
        
        connection.fetchval.return_value = 1  # Count > 0
        
        result = await service.tenant_has_phone_number(tenant_id)
        
        assert result is True
        connection.fetchval.assert_called_once()
        call_args = connection.fetchval.call_args[0]
        assert "COUNT(*)" in call_args[0]
        assert "tenant_id = $1" in call_args[0]
        assert "status != 'released'" in call_args[0]
        
    @pytest.mark.asyncio
    async def test_tenant_has_phone_number_false(self, database_service):
        """Test tenant has no phone number."""
        service, connection = database_service
        tenant_id = uuid4()
        
        connection.fetchval.return_value = 0  # Count = 0
        
        result = await service.tenant_has_phone_number(tenant_id)
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_get_total_phone_numbers(self, database_service):
        """Test getting total phone numbers count."""
        service, connection = database_service
        
        connection.fetchval.return_value = 42
        
        result = await service.get_total_phone_numbers()
        
        assert result == 42
        connection.fetchval.assert_called_once()
        call_args = connection.fetchval.call_args[0]
        assert 'SELECT COUNT(*) FROM phone_numbers' in call_args[0]
        
    @pytest.mark.asyncio
    async def test_get_active_phone_numbers_count(self, database_service):
        """Test getting active phone numbers count."""
        service, connection = database_service
        
        connection.fetchval.return_value = 25
        
        result = await service.get_active_phone_numbers_count()
        
        assert result == 25
        connection.fetchval.assert_called_once()
        call_args = connection.fetchval.call_args[0]
        assert 'SELECT COUNT(*) FROM phone_numbers' in call_args[0]
        assert "status IN ('provisioned', 'active')" in call_args[0]


class TestMessagingServiceOperations:
    """Test messaging service database operations."""
    
    @pytest.fixture
    def sample_messaging_service_data(self):
        """Sample messaging service data."""
        return {
            'id': uuid4(),
            'phone_number_id': uuid4(),
            'messaging_service_sid': 'MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
            'friendly_name': 'Test Messaging Service',
            'inbound_request_url': 'https://example.com/inbound',
            'status_callback_url': 'https://example.com/status',
            'created_at': datetime.now()
        }
    
    @pytest.fixture
    def database_service(self):
        """Create database service with mocked pool."""
        service = DatabaseService()
        pool = AsyncMock()
        connection = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = connection
        pool.acquire.return_value.__aexit__.return_value = None
        service.pool = pool
        return service, connection
    
    @pytest.mark.asyncio
    async def test_store_messaging_service(self, database_service, sample_messaging_service_data):
        """Test storing messaging service."""
        service, connection = database_service
        
        connection.fetchrow.return_value = sample_messaging_service_data
        
        messaging_service = MessagingService(**sample_messaging_service_data)
        result = await service.store_messaging_service(messaging_service)
        
        assert result is not None
        assert result.messaging_service_sid == 'MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'INSERT INTO messaging_services' in call_args[0]
        
    @pytest.mark.asyncio
    async def test_get_messaging_service(self, database_service, sample_messaging_service_data):
        """Test retrieving messaging service."""
        service, connection = database_service
        phone_number_id = sample_messaging_service_data['phone_number_id']
        
        connection.fetchrow.return_value = sample_messaging_service_data
        
        result = await service.get_messaging_service(phone_number_id)
        
        assert result is not None
        assert result.phone_number_id == phone_number_id
        
        connection.fetchrow.assert_called_once()
        call_args = connection.fetchrow.call_args[0]
        assert 'SELECT * FROM messaging_services WHERE phone_number_id = $1' in call_args[0]
        assert call_args[1] == phone_number_id


class TestErrorHandling:
    """Test database error handling."""
    
    @pytest.fixture
    def database_service(self):
        """Create database service with mocked pool."""
        service = DatabaseService()
        pool = AsyncMock()
        connection = AsyncMock()
        pool.acquire.return_value.__aenter__.return_value = connection
        pool.acquire.return_value.__aexit__.return_value = None
        service.pool = pool
        return service, connection
    
    @pytest.mark.asyncio
    async def test_database_connection_error(self, database_service):
        """Test handling database connection errors."""
        service, connection = database_service
        connection.fetchrow.side_effect = Exception("Connection lost")
        
        result = await service.get_phone_number_by_id(uuid4())
        
        assert result is None
        
    @pytest.mark.asyncio
    async def test_invalid_query_error(self, database_service):
        """Test handling invalid query errors."""
        service, connection = database_service
        connection.fetchval.side_effect = Exception("Invalid query")
        
        result = await service.get_total_phone_numbers()
        
        assert result == 0  # Should return 0 on error
        
    @pytest.mark.asyncio
    async def test_null_response_handling(self, database_service):
        """Test handling null database responses."""
        service, connection = database_service
        connection.fetchval.return_value = None
        
        result = await service.get_total_phone_numbers()
        
        assert result == 0  # Should handle None and return 0