"""Twilio API client service."""

import logging
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

from ..config.settings import settings, REQUIRED_CAPABILITIES
from ..models.phone_number import (
    AvailableNumber, PurchasedNumber, WebhookConfig, MessagingServiceResponse
)

logger = logging.getLogger(__name__)


class TwilioPhoneNumberService(ABC):
    """Abstract interface for Twilio phone number operations."""
    
    @abstractmethod
    async def search_available_numbers(self, area_code: str, limit: int = 10) -> List[AvailableNumber]:
        """Search for available phone numbers."""
        pass
    
    @abstractmethod
    async def purchase_number(self, phone_number: str) -> PurchasedNumber:
        """Purchase a phone number."""
        pass
    
    @abstractmethod
    async def configure_webhooks(self, sid: str, config: WebhookConfig) -> bool:
        """Configure webhooks for phone number."""
        pass
    
    @abstractmethod
    async def create_messaging_service(self, name: str, webhook_url: str) -> MessagingServiceResponse:
        """Create messaging service."""
        pass
    
    @abstractmethod
    async def add_number_to_messaging_service(self, messaging_service_sid: str, phone_number_sid: str) -> bool:
        """Add phone number to messaging service."""
        pass
    
    @abstractmethod
    async def release_number(self, sid: str) -> bool:
        """Release a phone number."""
        pass


class TwilioService(TwilioPhoneNumberService):
    """Production Twilio service implementation."""
    
    def __init__(self):
        self.client = TwilioClient(
            settings.twilio_account_sid, 
            settings.twilio_auth_token
        )
    
    async def search_available_numbers(self, area_code: str, limit: int = 10) -> List[AvailableNumber]:
        """Search for available phone numbers in area code."""
        try:
            available_numbers = self.client.available_phone_numbers('US').local.list(
                area_code=area_code,
                voice_enabled=True,
                sms_enabled=True,
                limit=limit
            )
            
            results = []
            for number in available_numbers:
                # Check capabilities
                capabilities = []
                if getattr(number, 'voice_enabled', False):
                    capabilities.append('voice')
                if getattr(number, 'sms_enabled', False):
                    capabilities.append('sms')
                
                # Only include numbers with required capabilities
                if all(cap in capabilities for cap in REQUIRED_CAPABILITIES):
                    results.append(AvailableNumber(
                        phone_number=number.phone_number,
                        friendly_name=getattr(number, 'friendly_name', ''),
                        capabilities=capabilities
                    ))
            
            logger.info(f"Found {len(results)} available numbers in area code {area_code}")
            return results
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error searching numbers: {e}")
            raise Exception(f"Failed to search available numbers: {e.msg}")
        except Exception as e:
            logger.error(f"Error searching available numbers: {e}")
            raise
    
    async def purchase_number(self, phone_number: str) -> PurchasedNumber:
        """Purchase a phone number."""
        try:
            incoming_phone_number = self.client.incoming_phone_numbers.create(
                phone_number=phone_number
            )
            
            logger.info(f"Successfully purchased phone number: {phone_number}")
            
            return PurchasedNumber(
                sid=incoming_phone_number.sid,
                phone_number=incoming_phone_number.phone_number,
                status=incoming_phone_number.status
            )
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error purchasing number: {e}")
            raise Exception(f"Failed to purchase number {phone_number}: {e.msg}")
        except Exception as e:
            logger.error(f"Error purchasing phone number: {e}")
            raise
    
    async def configure_webhooks(self, sid: str, config: WebhookConfig) -> bool:
        """Configure webhooks for phone number."""
        try:
            self.client.incoming_phone_numbers(sid).update(
                voice_url=config.voice_url,
                voice_method='POST',
                sms_url=config.sms_url,
                sms_method='POST',
                status_callback=config.status_callback_url,
                status_callback_method='POST'
            )
            
            logger.info(f"Successfully configured webhooks for {sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error configuring webhooks: {e}")
            raise Exception(f"Failed to configure webhooks: {e.msg}")
        except Exception as e:
            logger.error(f"Error configuring webhooks: {e}")
            raise
    
    async def create_messaging_service(self, name: str, webhook_url: str) -> MessagingServiceResponse:
        """Create messaging service."""
        try:
            service = self.client.messaging.v1.services.create(
                friendly_name=name,
                inbound_request_url=webhook_url,
                inbound_method='POST'
            )
            
            logger.info(f"Successfully created messaging service: {service.sid}")
            
            return MessagingServiceResponse(
                sid=service.sid,
                friendly_name=service.friendly_name
            )
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error creating messaging service: {e}")
            raise Exception(f"Failed to create messaging service: {e.msg}")
        except Exception as e:
            logger.error(f"Error creating messaging service: {e}")
            raise
    
    async def add_number_to_messaging_service(self, messaging_service_sid: str, phone_number_sid: str) -> bool:
        """Add phone number to messaging service."""
        try:
            self.client.messaging.v1.services(messaging_service_sid).phone_numbers.create(
                phone_number_sid=phone_number_sid
            )
            
            logger.info(f"Added phone number {phone_number_sid} to messaging service {messaging_service_sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error adding number to messaging service: {e}")
            raise Exception(f"Failed to add number to messaging service: {e.msg}")
        except Exception as e:
            logger.error(f"Error adding number to messaging service: {e}")
            raise
    
    async def release_number(self, sid: str) -> bool:
        """Release a phone number."""
        try:
            self.client.incoming_phone_numbers(sid).delete()
            
            logger.info(f"Successfully released phone number: {sid}")
            return True
            
        except TwilioRestException as e:
            logger.error(f"Twilio API error releasing number: {e}")
            raise Exception(f"Failed to release number: {e.msg}")
        except Exception as e:
            logger.error(f"Error releasing phone number: {e}")
            raise


class MockTwilioService(TwilioPhoneNumberService):
    """Mock Twilio service for testing."""
    
    def __init__(self):
        self.purchased_numbers = {}
        self.messaging_services = {}
        self.webhook_configs = {}
    
    async def search_available_numbers(self, area_code: str, limit: int = 10) -> List[AvailableNumber]:
        """Mock search for available numbers."""
        # Generate mock available numbers
        results = []
        for i in range(min(limit, 5)):  # Return up to 5 mock numbers
            phone_number = f"+1{area_code}555{1000 + i:04d}"
            results.append(AvailableNumber(
                phone_number=phone_number,
                friendly_name=f"({area_code}) 555-{1000 + i:04d}",
                capabilities=REQUIRED_CAPABILITIES.copy()
            ))
        
        return results
    
    async def purchase_number(self, phone_number: str) -> PurchasedNumber:
        """Mock purchase number."""
        sid = f"PN{len(self.purchased_numbers):032x}"
        purchased = PurchasedNumber(
            sid=sid,
            phone_number=phone_number,
            status="in-use"
        )
        
        self.purchased_numbers[sid] = purchased
        return purchased
    
    async def configure_webhooks(self, sid: str, config: WebhookConfig) -> bool:
        """Mock configure webhooks."""
        self.webhook_configs[sid] = config
        return True
    
    async def create_messaging_service(self, name: str, webhook_url: str) -> MessagingServiceResponse:
        """Mock create messaging service."""
        sid = f"MG{len(self.messaging_services):032x}"
        service = MessagingServiceResponse(
            sid=sid,
            friendly_name=name
        )
        
        self.messaging_services[sid] = {
            "service": service,
            "webhook_url": webhook_url,
            "phone_numbers": []
        }
        
        return service
    
    async def add_number_to_messaging_service(self, messaging_service_sid: str, phone_number_sid: str) -> bool:
        """Mock add number to messaging service."""
        if messaging_service_sid in self.messaging_services:
            self.messaging_services[messaging_service_sid]["phone_numbers"].append(phone_number_sid)
            return True
        return False
    
    async def release_number(self, sid: str) -> bool:
        """Mock release number."""
        if sid in self.purchased_numbers:
            del self.purchased_numbers[sid]
            return True
        return False


def get_twilio_service() -> TwilioPhoneNumberService:
    """Get Twilio service instance (production or mock)."""
    if settings.environment == "test":
        return MockTwilioService()
    else:
        return TwilioService()