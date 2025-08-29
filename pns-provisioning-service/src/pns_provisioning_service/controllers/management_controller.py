"""Phone number management endpoints."""

import logging
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends

from ..models.api import success_response, error_response, ErrorCodes
from ..models.phone_number import (
    PhoneNumberConfiguration, ReleasePhoneNumberRequest, ReleasePhoneNumberResponse
)
from ..services.provisioning_service import ProvisioningService
from ..utils.auth import verify_jwt_token, extract_tenant_id_from_token

logger = logging.getLogger(__name__)


def create_management_router(provisioning_service: ProvisioningService) -> APIRouter:
    """Create phone number management router."""
    
    router = APIRouter(prefix="/phone-numbers", tags=["Phone Number Management"])
    
    @router.get("/{phone_id}")
    async def get_phone_number_details(
        phone_id: UUID, 
        token_payload: dict = Depends(verify_jwt_token)
    ):
        """Get phone number details."""
        try:
            tenant_id = extract_tenant_id_from_token(token_payload)
            if not tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Invalid token: missing tenant information"
                )
            
            phone_record = await provisioning_service.get_phone_number_by_id(phone_id)
            
            if not phone_record:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"Phone number {phone_id} not found"
                )
            
            # Verify tenant owns this phone number
            if str(phone_record.tenant_id) != tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Access denied: phone number belongs to different tenant"
                )
            
            # Get messaging service info
            messaging_service = None
            if phone_record.messaging_service_sid:
                try:
                    messaging_service = await provisioning_service.database.get_messaging_service(phone_id)
                except Exception as e:
                    logger.warning(f"Could not get messaging service: {e}")
            
            response_data = {
                "phoneNumber": {
                    "id": str(phone_record.id),
                    "phoneNumber": phone_record.phone_number,
                    "friendlyName": phone_record.friendly_name,
                    "status": phone_record.status,
                    "capabilities": phone_record.capabilities,
                    "webhookUrls": {
                        "voice": phone_record.voice_webhook_url,
                        "sms": phone_record.sms_webhook_url
                    }
                }
            }
            
            if messaging_service:
                response_data["phoneNumber"]["messagingService"] = {
                    "sid": messaging_service.messaging_service_sid,
                    "friendlyName": messaging_service.friendly_name
                }
            
            return success_response(response_data)
            
        except Exception as e:
            logger.error(f"Error getting phone number details: {e}")
            return error_response(
                ErrorCodes.INTERNAL_SERVER_ERROR,
                f"Failed to get phone number details: {str(e)}"
            )
    
    @router.post("/{phone_id}/release")
    async def release_phone_number(
        phone_id: UUID,
        release_request: ReleasePhoneNumberRequest,
        token_payload: dict = Depends(verify_jwt_token)
    ):
        """Release phone number (future use)."""
        try:
            tenant_id = extract_tenant_id_from_token(token_payload)
            if not tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Invalid token: missing tenant information"
                )
            
            if not release_request.confirm_release:
                return error_response(
                    ErrorCodes.INVALID_REQUEST,
                    "Release confirmation required"
                )
            
            phone_record = await provisioning_service.get_phone_number_by_id(phone_id)
            
            if not phone_record:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"Phone number {phone_id} not found"
                )
            
            # Verify tenant owns this phone number
            if str(phone_record.tenant_id) != tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Access denied: phone number belongs to different tenant"
                )
            
            # Release the number
            released_phone = await provisioning_service.release_phone_number(
                phone_id, release_request.reason, confirmed=True
            )
            
            if not released_phone:
                return error_response(
                    ErrorCodes.INTERNAL_SERVER_ERROR,
                    "Failed to release phone number"
                )
            
            return success_response({
                "phoneNumber": {
                    "id": str(released_phone.id),
                    "status": released_phone.status,
                    "releasedAt": released_phone.date_released.isoformat() if released_phone.date_released else None,
                    "releaseReason": released_phone.status_reason
                }
            })
            
        except Exception as e:
            logger.error(f"Error releasing phone number: {e}")
            return error_response(
                ErrorCodes.INTERNAL_SERVER_ERROR,
                f"Failed to release phone number: {str(e)}"
            )
    
    @router.get("/{phone_id}/configuration")
    async def get_phone_number_configuration(
        phone_id: UUID,
        token_payload: dict = Depends(verify_jwt_token)
    ):
        """Get phone number configuration."""
        try:
            tenant_id = extract_tenant_id_from_token(token_payload)
            if not tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Invalid token: missing tenant information"
                )
            
            phone_record = await provisioning_service.get_phone_number_by_id(phone_id)
            
            if not phone_record:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"Phone number {phone_id} not found"
                )
            
            # Verify tenant owns this phone number
            if str(phone_record.tenant_id) != tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Access denied: phone number belongs to different tenant"
                )
            
            configuration = await provisioning_service.get_phone_number_configuration(phone_id)
            
            if not configuration:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    "Phone number configuration not found"
                )
            
            return success_response({"configuration": configuration})
            
        except Exception as e:
            logger.error(f"Error getting phone number configuration: {e}")
            return error_response(
                ErrorCodes.INTERNAL_SERVER_ERROR,
                f"Failed to get configuration: {str(e)}"
            )
    
    @router.put("/{phone_id}/configuration")
    async def update_phone_number_configuration(
        phone_id: UUID,
        config: PhoneNumberConfiguration,
        token_payload: dict = Depends(verify_jwt_token)
    ):
        """Update phone number configuration."""
        try:
            tenant_id = extract_tenant_id_from_token(token_payload)
            if not tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Invalid token: missing tenant information"
                )
            
            phone_record = await provisioning_service.get_phone_number_by_id(phone_id)
            
            if not phone_record:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"Phone number {phone_id} not found"
                )
            
            # Verify tenant owns this phone number
            if str(phone_record.tenant_id) != tenant_id:
                return error_response(
                    ErrorCodes.UNAUTHORIZED_ACCESS,
                    "Access denied: phone number belongs to different tenant"
                )
            
            # Build configuration update data
            config_data = {}
            if config.friendly_name:
                config_data["friendly_name"] = config.friendly_name
            
            if config.webhooks:
                if "voiceUrl" in config.webhooks:
                    config_data["voice_webhook_url"] = config.webhooks["voiceUrl"]
                if "smsUrl" in config.webhooks:
                    config_data["sms_webhook_url"] = config.webhooks["smsUrl"]
                if "statusCallbackUrl" in config.webhooks:
                    config_data["status_callback_url"] = config.webhooks["statusCallbackUrl"]
            
            if not config_data:
                return error_response(
                    ErrorCodes.INVALID_REQUEST,
                    "No configuration updates provided"
                )
            
            updated_phone = await provisioning_service.update_phone_number_configuration(
                phone_id, config_data
            )
            
            if not updated_phone:
                return error_response(
                    ErrorCodes.INTERNAL_SERVER_ERROR,
                    "Failed to update configuration"
                )
            
            # Return updated configuration
            updated_config = {}
            if "friendly_name" in config_data:
                updated_config["friendlyName"] = updated_phone.friendly_name
            
            if any(key in config_data for key in ["voice_webhook_url", "sms_webhook_url", "status_callback_url"]):
                updated_config["webhooks"] = {
                    "voiceUrl": updated_phone.voice_webhook_url,
                    "smsUrl": updated_phone.sms_webhook_url,
                    "statusCallbackUrl": updated_phone.status_callback_url
                }
            
            updated_config["updatedAt"] = updated_phone.updated_at.isoformat()
            
            return success_response({
                "configuration": updated_config
            })
            
        except Exception as e:
            logger.error(f"Error updating phone number configuration: {e}")
            
            if "webhook" in str(e).lower():
                return error_response(
                    ErrorCodes.WEBHOOK_CONFIGURATION_FAILED,
                    f"Webhook configuration failed: {str(e)}"
                )
            else:
                return error_response(
                    ErrorCodes.INTERNAL_SERVER_ERROR,
                    f"Failed to update configuration: {str(e)}"
                )
    
    return router