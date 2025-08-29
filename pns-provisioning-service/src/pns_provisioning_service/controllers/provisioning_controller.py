"""Phone number provisioning endpoints."""

import logging
from typing import Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends

from ..models.api import success_response, error_response, ErrorCodes
from ..models.phone_number import (
    ProvisionPhoneNumberRequest, ProvisionPhoneNumberResponse,
    PhoneNumberLookupResponse, PhoneNumberTenantResponse,
    PhoneNumberStatusUpdate
)
from ..services.provisioning_service import ProvisioningService
from ..utils.auth import verify_internal_service_key

logger = logging.getLogger(__name__)


def create_provisioning_router(provisioning_service: ProvisioningService) -> APIRouter:
    """Create phone number provisioning router."""
    
    router = APIRouter(prefix="/phone-numbers", tags=["Phone Number Provisioning"])
    
    @router.post("/provision", dependencies=[Depends(verify_internal_service_key)])
    async def provision_phone_number(request: ProvisionPhoneNumberRequest):
        """Provision new phone number for tenant."""
        try:
            logger.info(f"Provisioning phone number for tenant {request.tenant_id} in area code {request.area_code}")
            
            result = await provisioning_service.provision_phone_number(request)
            
            if result["success"]:
                return success_response(result["phoneNumber"], "Phone number provisioned successfully")
            else:
                return error_response(
                    ErrorCodes.NUMBER_PROVISIONING_FAILED,
                    "Failed to provision phone number",
                    result
                )
            
        except Exception as e:
            logger.error(f"Error provisioning phone number: {e}")
            
            # Map specific errors to error codes
            error_message = str(e)
            if "already has a phone number" in error_message:
                return error_response(
                    ErrorCodes.TENANT_ALREADY_HAS_NUMBER,
                    error_message
                )
            elif "not supported" in error_message:
                return error_response(
                    ErrorCodes.INVALID_AREA_CODE,
                    error_message
                )
            elif "No available numbers" in error_message:
                return error_response(
                    ErrorCodes.NUMBER_PROVISIONING_FAILED,
                    error_message,
                    {"areaCode": request.area_code}
                )
            else:
                return error_response(
                    ErrorCodes.NUMBER_PROVISIONING_FAILED,
                    f"Provisioning failed: {error_message}"
                )
    
    @router.get("/lookup/{phone_number}", dependencies=[Depends(verify_internal_service_key)])
    async def lookup_phone_number(phone_number: str):
        """Resolve phone number to tenantId (internal use)."""
        try:
            # Ensure E.164 format
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
            
            phone_record = await provisioning_service.get_phone_number_by_number(phone_number)
            
            if not phone_record:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"Phone number {phone_number} not found"
                )
            
            return success_response({
                "tenantId": str(phone_record.tenant_id),
                "phoneNumber": phone_record.phone_number,
                "status": phone_record.status
            })
            
        except Exception as e:
            logger.error(f"Error looking up phone number {phone_number}: {e}")
            return error_response(
                ErrorCodes.INTERNAL_SERVER_ERROR,
                f"Lookup failed: {str(e)}"
            )
    
    @router.get("/tenant/{tenant_id}", dependencies=[Depends(verify_internal_service_key)])
    async def get_phone_number_for_tenant(tenant_id: UUID):
        """Get phone number for tenant."""
        try:
            phone_record = await provisioning_service.get_phone_number_by_tenant(tenant_id)
            
            if not phone_record:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"No phone number found for tenant {tenant_id}"
                )
            
            return success_response({
                "phoneNumber": {
                    "id": str(phone_record.id),
                    "tenantId": str(phone_record.tenant_id),
                    "phoneNumber": phone_record.phone_number,
                    "phoneNumberSid": phone_record.phone_number_sid,
                    "messagingServiceSid": phone_record.messaging_service_sid,
                    "status": phone_record.status,
                    "webhooksConfigured": phone_record.webhooks_configured,
                    "dateProvisioned": phone_record.date_provisioned.isoformat() if phone_record.date_provisioned else None
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting phone number for tenant {tenant_id}: {e}")
            return error_response(
                ErrorCodes.INTERNAL_SERVER_ERROR,
                f"Failed to get phone number: {str(e)}"
            )
    
    @router.put("/{phone_id}/status", dependencies=[Depends(verify_internal_service_key)])
    async def update_phone_number_status(phone_id: UUID, status_update: PhoneNumberStatusUpdate):
        """Update phone number status."""
        try:
            updated_phone = await provisioning_service.update_phone_number_status(
                phone_id, status_update.status, status_update.reason
            )
            
            if not updated_phone:
                return error_response(
                    ErrorCodes.PHONE_NUMBER_NOT_FOUND,
                    f"Phone number {phone_id} not found"
                )
            
            return success_response({
                "phoneNumber": {
                    "id": str(updated_phone.id),
                    "status": updated_phone.status,
                    "statusReason": updated_phone.status_reason,
                    "updatedAt": updated_phone.updated_at.isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error updating phone number status: {e}")
            return error_response(
                ErrorCodes.INTERNAL_SERVER_ERROR,
                f"Status update failed: {str(e)}"
            )
    
    return router