"""
Unit tests for AS Alerts Service database operations.

Tests database functions with heavy mocking following unittest patterns
and "honest failure over eager passing" principle.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException

from main import (
    AlertSeverity,
    AlertStatus,
    AlertCreate,
    Alert,
    AlertStats,
    init_database,
    close_database,
    get_db_connection,
    create_alert_in_db,
    get_alerts_from_db,
    get_alert_by_id,
    update_alert_status,
    get_alert_stats_from_db
)


class TestDatabaseConnection(unittest.TestCase):
    """Test database connection management enforces real deployment scenarios."""
    
    @patch('main.asyncpg')
    async def test_init_database_creates_connection_pool(self, mock_asyncpg):
        """Test init_database creates asyncpg connection pool successfully."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        
        # Setup pool creation
        mock_asyncpg.create_pool.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchval.return_value = 1
        
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://test@localhost/test'}):
            await init_database()
        
        # Verify pool creation with correct parameters
        mock_asyncpg.create_pool.assert_called_once_with(
            'postgresql://test@localhost/test',
            min_size=1,
            max_size=5,
            command_timeout=60
        )
        
        # Verify connection test
        mock_connection.fetchval.assert_called_once_with("SELECT 1")
    
    @patch('main.asyncpg')
    async def test_init_database_handles_connection_failure(self, mock_asyncpg):
        """Test init_database handles database connection failures properly."""
        mock_asyncpg.create_pool.side_effect = Exception("Connection refused")
        
        with self.assertRaises(Exception) as context:
            await init_database()
        
        self.assertIn("Connection refused", str(context.exception))
    
    @patch('main.db_pool')
    async def test_close_database_closes_pool(self, mock_pool):
        """Test close_database properly closes connection pool."""
        mock_pool.close = AsyncMock()
        
        await close_database()
        
        mock_pool.close.assert_called_once()
    
    @patch('main.db_pool', None)
    async def test_get_db_connection_raises_when_pool_unavailable(self):
        """Test get_db_connection raises HTTPException when pool is None."""
        with self.assertRaises(HTTPException) as context:
            await get_db_connection()
        
        error = context.exception
        self.assertEqual(error.status_code, 503)
        self.assertEqual(error.detail, "Database not available")
    
    @patch('main.db_pool')
    async def test_get_db_connection_returns_pool(self, mock_pool):
        """Test get_db_connection returns the database pool."""
        result = await get_db_connection()
        
        self.assertEqual(result, mock_pool)


class TestCreateAlertInDb(unittest.TestCase):
    """Test create_alert_in_db enforces real alert creation business logic."""
    
    @patch('main.get_db_connection')
    async def test_create_alert_inserts_with_correct_data(self, mock_get_db):
        """Test create_alert_in_db inserts alert with proper field mapping."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Mock database response
        alert_id = str(uuid4())
        tenant_id = str(uuid4())
        created_time = datetime.utcnow()
        
        mock_row = {
            'id': alert_id,
            'tenant_id': tenant_id,
            'rule_name': 'high_cpu_usage',
            'message': 'CPU usage exceeded threshold',
            'severity': 'high',
            'status': 'triggered',
            'created_at': created_time,
            'updated_at': created_time,
            'acknowledged_at': None,
            'acknowledgment_note': None,
            'resolved_at': None,
            'resolution_note': None
        }
        mock_connection.fetchrow.return_value = mock_row
        
        # Create test data
        alert_data = AlertCreate(
            tenant_id=tenant_id,
            rule_name="high_cpu_usage",
            message="CPU usage exceeded threshold",
            severity=AlertSeverity.HIGH
        )
        
        with patch('main.uuid.uuid4', return_value=alert_id):
            with patch('main.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = created_time
                
                result = await create_alert_in_db(alert_data)
        
        # Verify database insert was called
        mock_connection.execute.assert_called_once()
        insert_call = mock_connection.execute.call_args
        
        # Verify SQL parameters
        sql_params = insert_call[0]
        self.assertEqual(sql_params[1], alert_id)  # id
        self.assertEqual(sql_params[2], tenant_id)  # tenant_id
        self.assertEqual(sql_params[3], "high_cpu_usage")  # rule_name
        self.assertEqual(sql_params[4], "CPU usage exceeded threshold")  # message
        self.assertEqual(sql_params[5], "high")  # severity
        self.assertEqual(sql_params[6], "triggered")  # status
        
        # Verify return value
        self.assertIsInstance(result, Alert)
        self.assertEqual(result.id, alert_id)
        self.assertEqual(result.tenant_id, tenant_id)
        self.assertEqual(result.severity, AlertSeverity.HIGH)
        self.assertEqual(result.status, AlertStatus.TRIGGERED)
    
    @patch('main.get_db_connection')
    async def test_create_alert_handles_database_error(self, mock_get_db):
        """Test create_alert_in_db properly handles database errors."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Simulate database error
        mock_connection.execute.side_effect = Exception("Database constraint violation")
        
        alert_data = AlertCreate(
            tenant_id=str(uuid4()),
            rule_name="test_rule",
            message="test message"
        )
        
        with self.assertRaises(Exception) as context:
            await create_alert_in_db(alert_data)
        
        self.assertIn("Database constraint violation", str(context.exception))


class TestGetAlertsFromDb(unittest.TestCase):
    """Test get_alerts_from_db enforces tenant isolation and filtering logic."""
    
    @patch('main.get_db_connection')
    async def test_get_alerts_basic_tenant_query(self, mock_get_db):
        """Test get_alerts_from_db retrieves alerts for specific tenant."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        tenant_id = str(uuid4())
        mock_rows = [
            {
                'id': str(uuid4()),
                'tenant_id': tenant_id,
                'rule_name': 'rule1',
                'message': 'message1',
                'severity': 'medium',
                'status': 'triggered',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'acknowledged_at': None,
                'acknowledgment_note': None,
                'resolved_at': None,
                'resolution_note': None
            }
        ]
        mock_connection.fetch.return_value = mock_rows
        
        result = await get_alerts_from_db(tenant_id)
        
        # Verify query called with tenant isolation
        mock_connection.fetch.assert_called_once()
        query_call = mock_connection.fetch.call_args
        self.assertIn("WHERE tenant_id = $1", query_call[0][0])
        self.assertEqual(query_call[0][1], tenant_id)
        
        # Verify results
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], Alert)
        self.assertEqual(result[0].tenant_id, tenant_id)
    
    @patch('main.get_db_connection')
    async def test_get_alerts_with_status_filter(self, mock_get_db):
        """Test get_alerts_from_db applies status filtering correctly."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []
        
        tenant_id = str(uuid4())
        status_filter = "acknowledged"
        
        await get_alerts_from_db(tenant_id, status=status_filter)
        
        # Verify query includes status filter
        query_call = mock_connection.fetch.call_args
        query_sql = query_call[0][0]
        query_params = query_call[0][1:]
        
        self.assertIn("WHERE tenant_id = $1", query_sql)
        self.assertIn("AND status = $2", query_sql)
        self.assertEqual(query_params[0], tenant_id)
        self.assertEqual(query_params[1], status_filter)
    
    @patch('main.get_db_connection')
    async def test_get_alerts_with_severity_filter(self, mock_get_db):
        """Test get_alerts_from_db applies severity filtering correctly."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []
        
        tenant_id = str(uuid4())
        severity_filter = "critical"
        
        await get_alerts_from_db(tenant_id, severity=severity_filter)
        
        # Verify query includes severity filter
        query_call = mock_connection.fetch.call_args
        query_sql = query_call[0][0]
        query_params = query_call[0][1:]
        
        self.assertIn("WHERE tenant_id = $1", query_sql)
        self.assertIn("AND severity = $2", query_sql)
        self.assertEqual(query_params[0], tenant_id)
        self.assertEqual(query_params[1], severity_filter)
    
    @patch('main.get_db_connection')
    async def test_get_alerts_with_both_filters(self, mock_get_db):
        """Test get_alerts_from_db applies both status and severity filters."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []
        
        tenant_id = str(uuid4())
        
        await get_alerts_from_db(tenant_id, status="triggered", severity="high")
        
        # Verify query includes both filters
        query_call = mock_connection.fetch.call_args
        query_sql = query_call[0][0]
        query_params = query_call[0][1:]
        
        self.assertIn("WHERE tenant_id = $1", query_sql)
        self.assertIn("AND status = $2", query_sql)
        self.assertIn("AND severity = $3", query_sql)
        self.assertEqual(len(query_params), 4)  # tenant_id, status, severity, limit
    
    @patch('main.get_db_connection')
    async def test_get_alerts_enforces_limit(self, mock_get_db):
        """Test get_alerts_from_db enforces result limit to prevent abuse."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetch.return_value = []
        
        tenant_id = str(uuid4())
        custom_limit = 25
        
        await get_alerts_from_db(tenant_id, limit=custom_limit)
        
        # Verify LIMIT clause and parameter
        query_call = mock_connection.fetch.call_args
        query_sql = query_call[0][0]
        query_params = query_call[0][1:]
        
        self.assertIn("LIMIT $", query_sql)
        self.assertEqual(query_params[-1], custom_limit)


class TestGetAlertById(unittest.TestCase):
    """Test get_alert_by_id enforces UUID validation and proper data retrieval."""
    
    @patch('main.get_db_connection')
    async def test_get_alert_by_id_with_valid_uuid(self, mock_get_db):
        """Test get_alert_by_id retrieves alert with valid UUID."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        alert_id = str(uuid4())
        mock_row = {
            'id': alert_id,
            'tenant_id': str(uuid4()),
            'rule_name': 'test_rule',
            'message': 'test message',
            'severity': 'medium',
            'status': 'triggered',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'acknowledged_at': None,
            'acknowledgment_note': None,
            'resolved_at': None,
            'resolution_note': None
        }
        mock_connection.fetchrow.return_value = mock_row
        
        result = await get_alert_by_id(alert_id)
        
        # Verify query called with correct alert_id
        mock_connection.fetchrow.assert_called_once()
        query_call = mock_connection.fetchrow.call_args
        self.assertEqual(query_call[0][1], alert_id)
        
        # Verify result
        self.assertIsInstance(result, Alert)
        self.assertEqual(result.id, alert_id)
    
    async def test_get_alert_by_id_with_invalid_uuid(self):
        """Test get_alert_by_id returns None for invalid UUID format."""
        invalid_ids = ["not-a-uuid", "123", "", "too-short-uuid"]
        
        for invalid_id in invalid_ids:
            with self.subTest(invalid_id=invalid_id):
                result = await get_alert_by_id(invalid_id)
                self.assertIsNone(result)
    
    @patch('main.get_db_connection')
    async def test_get_alert_by_id_not_found(self, mock_get_db):
        """Test get_alert_by_id returns None when alert doesn't exist."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        mock_connection.fetchrow.return_value = None
        
        alert_id = str(uuid4())
        result = await get_alert_by_id(alert_id)
        
        self.assertIsNone(result)


class TestUpdateAlertStatus(unittest.TestCase):
    """Test update_alert_status enforces workflow states and proper field updates."""
    
    @patch('main.get_db_connection')
    async def test_update_alert_to_acknowledged(self, mock_get_db):
        """Test update_alert_status properly updates to acknowledged status."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        alert_id = str(uuid4())
        acknowledgment_note = "Investigating with team"
        
        mock_row = {
            'id': alert_id,
            'tenant_id': str(uuid4()),
            'rule_name': 'test_rule',
            'message': 'test message',
            'severity': 'high',
            'status': 'acknowledged',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'acknowledged_at': datetime.utcnow(),
            'acknowledgment_note': acknowledgment_note,
            'resolved_at': None,
            'resolution_note': None
        }
        mock_connection.fetchrow.return_value = mock_row
        
        with patch('main.datetime') as mock_datetime:
            mock_now = datetime.utcnow()
            mock_datetime.utcnow.return_value = mock_now
            
            result = await update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED, acknowledgment_note)
        
        # Verify update query called with acknowledged fields
        mock_connection.execute.assert_called_once()
        update_call = mock_connection.execute.call_args
        update_params = update_call[0]
        
        self.assertEqual(update_params[1], "acknowledged")  # status
        self.assertEqual(update_params[4], acknowledgment_note)  # note
        self.assertEqual(update_params[5], alert_id)  # alert_id
        
        # Verify result
        self.assertIsInstance(result, Alert)
        self.assertEqual(result.status, AlertStatus.ACKNOWLEDGED)
    
    @patch('main.get_db_connection')
    async def test_update_alert_to_resolved(self, mock_get_db):
        """Test update_alert_status properly updates to resolved status."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        alert_id = str(uuid4())
        resolution_note = "Fixed by restarting service"
        
        mock_row = {
            'id': alert_id,
            'tenant_id': str(uuid4()),
            'rule_name': 'test_rule',
            'message': 'test message',
            'severity': 'medium',
            'status': 'resolved',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'acknowledged_at': datetime.utcnow(),
            'acknowledgment_note': 'Previously acknowledged',
            'resolved_at': datetime.utcnow(),
            'resolution_note': resolution_note
        }
        mock_connection.fetchrow.return_value = mock_row
        
        result = await update_alert_status(alert_id, AlertStatus.RESOLVED, resolution_note)
        
        # Verify update query called with resolved fields
        mock_connection.execute.assert_called_once()
        update_call = mock_connection.execute.call_args
        update_params = update_call[0]
        
        self.assertEqual(update_params[1], "resolved")  # status
        self.assertEqual(update_params[4], resolution_note)  # note
        self.assertEqual(update_params[5], alert_id)  # alert_id
        
        # Verify result
        self.assertIsInstance(result, Alert)
        self.assertEqual(result.status, AlertStatus.RESOLVED)


class TestGetAlertStatsFromDb(unittest.TestCase):
    """Test get_alert_stats_from_db provides accurate tenant statistics."""
    
    @patch('main.get_db_connection')
    async def test_get_alert_stats_with_realistic_data(self, mock_get_db):
        """Test get_alert_stats_from_db calculates correct statistics."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # Mock database responses for different queries
        mock_connection.fetchval.side_effect = [
            25,  # total
            8,   # triggered
            5,   # acknowledged
            12   # resolved
        ]
        
        tenant_id = str(uuid4())
        result = await get_alert_stats_from_db(tenant_id)
        
        # Verify all queries called with correct tenant_id
        self.assertEqual(mock_connection.fetchval.call_count, 4)
        for call in mock_connection.fetchval.call_args_list:
            self.assertEqual(call[0][1], tenant_id)  # tenant_id parameter
        
        # Verify result statistics
        self.assertIsInstance(result, AlertStats)
        self.assertEqual(result.total, 25)
        self.assertEqual(result.triggered, 8)
        self.assertEqual(result.acknowledged, 5)
        self.assertEqual(result.resolved, 12)
    
    @patch('main.get_db_connection')
    async def test_get_alert_stats_for_new_tenant(self, mock_get_db):
        """Test get_alert_stats_from_db handles new tenant with zero alerts."""
        mock_pool = AsyncMock()
        mock_connection = AsyncMock()
        mock_get_db.return_value = mock_pool
        mock_pool.acquire.return_value.__aenter__.return_value = mock_connection
        
        # All counts are zero for new tenant
        mock_connection.fetchval.side_effect = [0, 0, 0, 0]
        
        tenant_id = str(uuid4())
        result = await get_alert_stats_from_db(tenant_id)
        
        # Verify zero statistics
        self.assertEqual(result.total, 0)
        self.assertEqual(result.triggered, 0)
        self.assertEqual(result.acknowledged, 0)
        self.assertEqual(result.resolved, 0)


if __name__ == '__main__':
    unittest.main()