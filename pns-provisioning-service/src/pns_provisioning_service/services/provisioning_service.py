"""Phone number provisioning service."""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from ..config.settings import settings, WEBHOOK_CONFIG, SUPPORTED_AREA_CODES
from ..models.phone_number import (
    PhoneNumber, ProvisionPhoneNumberRequest, WebhookConfig,
    MessagingService
)
from ..models.api import ErrorCodes
from .database import DatabaseService
from .twilio_client import TwilioPhoneNumberService, get_twilio_service

logger = logging.getLogger(__name__)


class ProvisioningService:
    """Handles phone number provisioning workflow."""
    
    def __init__(self, database: DatabaseService):
        self.database = database
        self.twilio_service: TwilioPhoneNumberService = get_twilio_service()
        self._provisioning_locks: Dict[UUID, asyncio.Lock] = {}
    
    async def provision_phone_number(self, request: ProvisionPhoneNumberRequest) -> Dict[str, Any]:
        """
        Complete phone number provisioning workflow.
        
        1. Validate request and check constraints
        2. Search for available numbers
        3. Purchase number from Twilio
        4. Create messaging service
        5. Configure webhooks
        6. Store in database
        7. Return success response
        """
        try:
            # Acquire lock for tenant to prevent concurrent provisioning
            if request.tenant_id not in self._provisioning_locks:
                self._provisioning_locks[request.tenant_id] = asyncio.Lock()
            
            async with self._provisioning_locks[request.tenant_id]:
                return await self._provision_phone_number_locked(request)
                
        except Exception as e:
            logger.error(f"Error in phone number provisioning: {e}")
            raise
        finally:
            # Clean up lock if possible
            if request.tenant_id in self._provisioning_locks:
                try:
                    # Only remove if no one else is waiting
                    if not self._provisioning_locks[request.tenant_id].locked():
                        del self._provisioning_locks[request.tenant_id]
                except:
                    pass
    
    async def _provision_phone_number_locked(self, request: ProvisionPhoneNumberRequest) -> Dict[str, Any]:
        """Provision phone number with tenant lock acquired."""
        # Step 1: Validate request
        validation_result = await self._validate_provisioning_request(request)
        if not validation_result["valid"]:
            raise Exception(validation_result["error"])
        
        # Step 2: Search for available numbers
        logger.info(f"Searching for available numbers in area code {request.area_code}")
        available_numbers = await self.twilio_service.search_available_numbers(
            request.area_code, limit=5
        )
        
        if not available_numbers:
            raise Exception(f"No available numbers in area code {request.area_code}")
        
        # Step 3: Purchase first available number
        selected_number = available_numbers[0]
        logger.info(f"Purchasing number: {selected_number.phone_number}")
        
        purchased_number = await self.twilio_service.purchase_number(
            selected_number.phone_number
        )
        
        phone_number_id = uuid4()
        rollback_actions = []
        
        try:
            # Step 4: Create messaging service
            messaging_service_name = f"NMC-{request.tenant_id}-SMS"
            sms_webhook_url = f"{request.webhook_base_url}{settings.webhook_sms_path}"
            
            logger.info(f"Creating messaging service: {messaging_service_name}")
            messaging_service = await self.twilio_service.create_messaging_service(
                messaging_service_name, sms_webhook_url
            )
            rollback_actions.append(("delete_messaging_service", messaging_service.sid))
            
            # Step 5: Add number to messaging service
            await self.twilio_service.add_number_to_messaging_service(
                messaging_service.sid, purchased_number.sid
            )
            
            # Step 6: Configure webhooks
            webhook_config = WebhookConfig(
                voice_url=f"{request.webhook_base_url}{settings.webhook_voice_path}",
                sms_url=f"{request.webhook_base_url}{settings.webhook_sms_path}",
                status_callback_url=f"{request.webhook_base_url}{settings.webhook_status_path}"
            )
            
            logger.info(f"Configuring webhooks for {purchased_number.sid}")
            await self.twilio_service.configure_webhooks(purchased_number.sid, webhook_config)
            
            # Step 7: Store in database
            phone_data = {
                "id": phone_number_id,
                "tenant_id": request.tenant_id,
                "phone_number": purchased_number.phone_number,
                "phone_number_sid": purchased_number.sid,
                "messaging_service_sid": messaging_service.sid,
                "area_code": request.area_code,
                "region": "US",
                "number_type": request.number_type,
                "capabilities": ["voice", "sms"],
                "status": "provisioned",
                "date_provisioned": datetime.utcnow(),
                "webhooks_configured": True,
                "voice_webhook_url": webhook_config.voice_url,
                "sms_webhook_url": webhook_config.sms_url,
                "status_callback_url": webhook_config.status_callback_url,
                "monthly_price_cents": 100,  # $1.00 standard rate
                "setup_price_cents": 0,     # Usually free
                "currency": "USD"
            }
            
            phone_number = await self.database.create_phone_number(phone_data)
            if not phone_number:
                raise Exception("Failed to store phone number in database")
            
            # Step 8: Create messaging service record
            messaging_service_data = {
                "phone_number_id": phone_number_id,
                "messaging_service_sid": messaging_service.sid,
                "friendly_name": messaging_service_name,
                "inbound_webhook_url": sms_webhook_url,
                "inbound_method": "POST"
            }
            
            await self.database.create_messaging_service(messaging_service_data)
            
            logger.info(f"Successfully provisioned phone number {purchased_number.phone_number} for tenant {request.tenant_id}")
            
            return {
                "success": True,
                "phoneNumber": {
                    "id": str(phone_number.id),
                    "tenantId": str(phone_number.tenant_id),
                    "phoneNumber": phone_number.phone_number,
                    "phoneNumberSid": phone_number.phone_number_sid,
                    "messagingServiceSid": phone_number.messaging_service_sid,
                    "areaCode": phone_number.area_code,
                    "region": phone_number.region,
                    "status": phone_number.status,
                    "webhooksConfigured": phone_number.webhooks_configured,
                    "monthlyPriceCents": phone_number.monthly_price_cents,
                    "provisionedAt": phone_number.date_provisioned.isoformat() if phone_number.date_provisioned else None
                }
            }
            
        except Exception as e:
            # Rollback on failure
            logger.error(f"Provisioning failed, performing rollback: {e}")
            await self._perform_rollback(purchased_number.sid, rollback_actions)
            raise
    
    async def _validate_provisioning_request(self, request: ProvisionPhoneNumberRequest) -> Dict[str, Any]:
        """Validate provisioning request."""
        try:
            # Check if area code is supported
            if request.area_code not in SUPPORTED_AREA_CODES:
                return {
                    "valid": False,
                    "error": f"Area code {request.area_code} is not supported"
                }
            
            # Check if tenant already has a phone number (Phase 1 constraint)
            if await self.database.tenant_has_phone_number(request.tenant_id):
                return {
                    "valid": False,
                    "error": "Tenant already has a phone number (one per tenant limit)"
                }
            
            # Validate webhook base URL
            if not request.webhook_base_url.startswith(("http://", "https://")):
                return {
                    "valid": False,
                    "error": "Invalid webhook base URL format"
                }
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Error validating provisioning request: {e}")
            return {
                "valid": False,
                "error": "Internal validation error"
            }
    
    async def _perform_rollback(self, phone_number_sid: str, rollback_actions: List[tuple]):
        """Perform rollback actions on failure."""
        try:
            # Release purchased number
            try:
                await self.twilio_service.release_number(phone_number_sid)
                logger.info(f"Rolled back: Released phone number {phone_number_sid}")
            except Exception as e:
                logger.error(f"Failed to rollback phone number release: {e}")
            
            # Perform other rollback actions
            for action, resource_id in rollback_actions:
                try:
                    if action == "delete_messaging_service":
                        # Note: Twilio doesn't provide easy messaging service deletion
                        # In production, you might want to disable it or handle cleanup later
                        logger.warning(f"Messaging service {resource_id} may need manual cleanup")
                except Exception as e:
                    logger.error(f"Failed rollback action {action} for {resource_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error during rollback: {e}")
    
    async def get_phone_number_by_tenant(self, tenant_id: UUID) -> Optional[PhoneNumber]:
        """Get phone number for tenant."""
        return await self.database.get_phone_number_by_tenant(tenant_id)
    
    async def get_phone_number_by_id(self, phone_id: UUID) -> Optional[PhoneNumber]:
        """Get phone number by ID."""
        return await self.database.get_phone_number_by_id(phone_id)
    
    async def get_phone_number_by_number(self, phone_number: str) -> Optional[PhoneNumber]:
        """Get phone number by phone number string."""
        return await self.database.get_phone_number_by_number(phone_number)
    
    async def update_phone_number_status(
        self, 
        phone_id: UUID, 
        status: str, 
        reason: Optional[str] = None
    ) -> Optional[PhoneNumber]:
        """Update phone number status."""
        return await self.database.update_phone_number_status(phone_id, status, reason)
    
    async def update_phone_number_configuration(
        self, 
        phone_id: UUID, 
        config_data: Dict[str, Any]
    ) -> Optional[PhoneNumber]:
        """Update phone number configuration."""
        # If webhooks are being updated, configure them in Twilio too
        phone_number = await self.database.get_phone_number_by_id(phone_id)
        if not phone_number:
            return None
        
        if any(key in config_data for key in ['voice_webhook_url', 'sms_webhook_url', 'status_callback_url']):
            try:
                webhook_config = WebhookConfig(
                    voice_url=config_data.get('voice_webhook_url', phone_number.voice_webhook_url),
                    sms_url=config_data.get('sms_webhook_url', phone_number.sms_webhook_url),
                    status_callback_url=config_data.get('status_callback_url', phone_number.status_callback_url or '')
                )
                
                await self.twilio_service.configure_webhooks(phone_number.phone_number_sid, webhook_config)
                
            except Exception as e:
                logger.error(f"Failed to update webhooks in Twilio: {e}")
                raise Exception("Failed to update webhook configuration")
        
        return await self.database.update_phone_number_configuration(phone_id, config_data)
    
    async def release_phone_number(
        self, 
        phone_id: UUID, 
        reason: str, 
        confirmed: bool = False
    ) -> Optional[PhoneNumber]:
        """Release phone number."""
        if not confirmed:
            raise Exception("Phone number release must be confirmed")
        
        phone_number = await self.database.get_phone_number_by_id(phone_id)
        if not phone_number:
            return None
        
        try:
            # Release from Twilio
            await self.twilio_service.release_number(phone_number.phone_number_sid)
            
            # Update database
            return await self.database.release_phone_number(phone_id, reason)
            
        except Exception as e:
            logger.error(f"Error releasing phone number: {e}")
            raise Exception(f"Failed to release phone number: {str(e)}")
    
    async def get_phone_number_configuration(self, phone_id: UUID) -> Optional[Dict[str, Any]]:
        """Get phone number configuration."""
        phone_number = await self.database.get_phone_number_by_id(phone_id)
        if not phone_number:
            return None
        
        messaging_service = await self.database.get_messaging_service(phone_id)
        
        config = {
            "phoneId": str(phone_number.id),
            "webhooks": {
                "voiceUrl": phone_number.voice_webhook_url,
                "voiceMethod": "POST",
                "smsUrl": phone_number.sms_webhook_url,
                "smsMethod": "POST",
                "statusCallbackUrl": phone_number.status_callback_url
            }
        }
        
        if messaging_service:
            config["messagingService"] = {
                "sid": messaging_service.messaging_service_sid,
                "inboundWebhookUrl": messaging_service.inbound_webhook_url
            }
        
        return config