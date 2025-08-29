"""Database connection and operations."""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import asyncpg
from uuid import UUID

from ..config.settings import settings
from ..models.phone_number import PhoneNumber, MessagingService

logger = logging.getLogger(__name__)


class DatabaseService:
    """Handles database operations for phone numbers."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self) -> bool:
        """Initialize database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=settings.database_pool_size,
                max_size=settings.database_pool_max,
                server_settings={
                    'application_name': settings.service_name,
                }
            )
            
            logger.info("Database connection pool initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.pool.acquire() as connection:
                await connection.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def create_phone_number(self, phone_data: Dict[str, Any]) -> Optional[PhoneNumber]:
        """Create a new phone number record."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow("""
                    INSERT INTO phone_numbers (
                        tenant_id, phone_number, phone_number_sid, messaging_service_sid,
                        friendly_name, area_code, region, number_type, capabilities,
                        status, date_provisioned, webhooks_configured,
                        voice_webhook_url, sms_webhook_url, status_callback_url,
                        monthly_price_cents, setup_price_cents, currency
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
                    ) RETURNING *
                """, 
                    phone_data["tenant_id"],
                    phone_data["phone_number"],
                    phone_data["phone_number_sid"],
                    phone_data.get("messaging_service_sid"),
                    phone_data.get("friendly_name"),
                    phone_data["area_code"],
                    phone_data.get("region", "US"),
                    phone_data.get("number_type", "local"),
                    phone_data.get("capabilities", ["voice", "sms"]),
                    phone_data.get("status", "provisioning"),
                    phone_data.get("date_provisioned"),
                    phone_data.get("webhooks_configured", False),
                    phone_data["voice_webhook_url"],
                    phone_data["sms_webhook_url"],
                    phone_data.get("status_callback_url"),
                    phone_data.get("monthly_price_cents", 100),
                    phone_data.get("setup_price_cents", 0),
                    phone_data.get("currency", "USD")
                )
                
                return PhoneNumber(**dict(row))
                
        except Exception as e:
            logger.error(f"Error creating phone number: {e}")
            return None
    
    async def get_phone_number_by_id(self, phone_id: UUID) -> Optional[PhoneNumber]:
        """Get phone number by ID."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    "SELECT * FROM phone_numbers WHERE id = $1", phone_id
                )
                
                if row:
                    return PhoneNumber(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting phone number {phone_id}: {e}")
            return None
    
    async def get_phone_number_by_tenant(self, tenant_id: UUID) -> Optional[PhoneNumber]:
        """Get phone number by tenant ID."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    "SELECT * FROM phone_numbers WHERE tenant_id = $1", tenant_id
                )
                
                if row:
                    return PhoneNumber(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting phone number for tenant {tenant_id}: {e}")
            return None
    
    async def get_phone_number_by_number(self, phone_number: str) -> Optional[PhoneNumber]:
        """Get phone number by phone number string."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    "SELECT * FROM phone_numbers WHERE phone_number = $1", phone_number
                )
                
                if row:
                    return PhoneNumber(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting phone number {phone_number}: {e}")
            return None
    
    async def update_phone_number_status(
        self, 
        phone_id: UUID, 
        status: str, 
        reason: Optional[str] = None
    ) -> Optional[PhoneNumber]:
        """Update phone number status."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow("""
                    UPDATE phone_numbers 
                    SET status = $2, status_reason = $3, updated_at = NOW()
                    WHERE id = $1
                    RETURNING *
                """, phone_id, status, reason)
                
                if row:
                    return PhoneNumber(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error updating phone number status: {e}")
            return None
    
    async def update_phone_number_configuration(
        self, 
        phone_id: UUID, 
        config_data: Dict[str, Any]
    ) -> Optional[PhoneNumber]:
        """Update phone number configuration."""
        try:
            async with self.pool.acquire() as connection:
                # Build dynamic update query based on provided fields
                set_clauses = []
                values = [phone_id]
                param_num = 2
                
                for field, value in config_data.items():
                    if field in ['friendly_name', 'voice_webhook_url', 'sms_webhook_url', 'status_callback_url']:
                        set_clauses.append(f"{field} = ${param_num}")
                        values.append(value)
                        param_num += 1
                
                if not set_clauses:
                    return await self.get_phone_number_by_id(phone_id)
                
                set_clauses.append(f"updated_at = NOW()")
                query = f"""
                    UPDATE phone_numbers 
                    SET {', '.join(set_clauses)}
                    WHERE id = $1
                    RETURNING *
                """
                
                row = await connection.fetchrow(query, *values)
                
                if row:
                    return PhoneNumber(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error updating phone number configuration: {e}")
            return None
    
    async def mark_webhooks_configured(self, phone_id: UUID) -> bool:
        """Mark phone number webhooks as configured."""
        try:
            async with self.pool.acquire() as connection:
                await connection.execute("""
                    UPDATE phone_numbers 
                    SET webhooks_configured = true, updated_at = NOW()
                    WHERE id = $1
                """, phone_id)
                
                return True
                
        except Exception as e:
            logger.error(f"Error marking webhooks configured: {e}")
            return False
    
    async def release_phone_number(
        self, 
        phone_id: UUID, 
        reason: str
    ) -> Optional[PhoneNumber]:
        """Release phone number."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow("""
                    UPDATE phone_numbers 
                    SET status = 'released', 
                        status_reason = $2,
                        date_released = NOW(),
                        updated_at = NOW()
                    WHERE id = $1
                    RETURNING *
                """, phone_id, reason)
                
                if row:
                    return PhoneNumber(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error releasing phone number: {e}")
            return None
    
    async def create_messaging_service(self, service_data: Dict[str, Any]) -> Optional[MessagingService]:
        """Create messaging service record."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow("""
                    INSERT INTO messaging_services (
                        phone_number_id, messaging_service_sid, friendly_name,
                        inbound_webhook_url, inbound_method, fallback_url, status_callback
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING *
                """,
                    service_data["phone_number_id"],
                    service_data["messaging_service_sid"],
                    service_data["friendly_name"],
                    service_data["inbound_webhook_url"],
                    service_data.get("inbound_method", "POST"),
                    service_data.get("fallback_url"),
                    service_data.get("status_callback")
                )
                
                if row:
                    return MessagingService(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error creating messaging service: {e}")
            return None
    
    async def get_messaging_service(self, phone_number_id: UUID) -> Optional[MessagingService]:
        """Get messaging service for phone number."""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    "SELECT * FROM messaging_services WHERE phone_number_id = $1", 
                    phone_number_id
                )
                
                if row:
                    return MessagingService(**dict(row))
                return None
                
        except Exception as e:
            logger.error(f"Error getting messaging service: {e}")
            return None
    
    async def tenant_has_phone_number(self, tenant_id: UUID) -> bool:
        """Check if tenant already has a phone number."""
        try:
            async with self.pool.acquire() as connection:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM phone_numbers WHERE tenant_id = $1 AND status != 'released'",
                    tenant_id
                )
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking tenant phone number: {e}")
            return False
    
    async def get_total_phone_numbers(self) -> int:
        """Get total count of phone numbers."""
        try:
            async with self.pool.acquire() as connection:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM phone_numbers"
                )
                return count or 0
                
        except Exception as e:
            logger.error(f"Error getting total phone numbers count: {e}")
            return 0
    
    async def get_active_phone_numbers_count(self) -> int:
        """Get count of active phone numbers."""
        try:
            async with self.pool.acquire() as connection:
                count = await connection.fetchval(
                    "SELECT COUNT(*) FROM phone_numbers WHERE status IN ('provisioned', 'active')"
                )
                return count or 0
                
        except Exception as e:
            logger.error(f"Error getting active phone numbers count: {e}")
            return 0