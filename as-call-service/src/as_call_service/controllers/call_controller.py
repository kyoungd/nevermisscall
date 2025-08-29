"""Call controller for handling call-related API endpoints."""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    CallResponse,
    CallWebhook,
)
from ..services import call_service
from ..utils import (
    logger,
    verify_internal_service_key,
    verify_jwt_token,
    verify_tenant_access,
    successResponse,
    errorResponse,
    ValidationError,
    DatabaseError,
    ServiceError,
)

router = APIRouter(prefix="/calls", tags=["calls"])


@router.post("/incoming", response_model=Dict[str, Any])
async def process_incoming_call(
    webhook_data: CallWebhook,
    _: str = Depends(verify_internal_service_key)
) -> Dict[str, Any]:
    """Process incoming call webhook from twilio-server."""
    try:
        logger.info(
            "Processing incoming call webhook",
            call_sid=webhook_data.callSid,
            from_phone=webhook_data.from_,
            to_phone=webhook_data.to
        )
        
        call = await call_service.process_incoming_call(webhook_data)
        
        return successResponse({
            "call": {
                "id": str(call.id),
                "callSid": call.call_sid,
                "status": call.status,
                "tenantId": str(call.tenant_id),
                "customerPhone": call.customer_phone,
                "businessPhone": call.business_phone,
            }
        }, "Call processed successfully")
        
    except ValidationError as e:
        logger.warning("Call validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error("Database error processing call", error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    except ServiceError as e:
        logger.error("Service error processing call", error=str(e))
        raise HTTPException(status_code=502, detail="External service error")
    except Exception as e:
        logger.error("Unexpected error processing incoming call", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/missed", response_model=Dict[str, Any])
async def process_missed_call(
    missed_call_data: Dict[str, Any],
    _: str = Depends(verify_internal_service_key)
) -> Dict[str, Any]:
    """Process missed call event and trigger SMS workflow."""
    try:
        call_sid = missed_call_data.get("callSid")
        if not call_sid:
            raise ValidationError("callSid is required")
        
        logger.info("Processing missed call", call_sid=call_sid)
        
        call = await call_service.process_missed_call(call_sid, missed_call_data)
        
        return successResponse({
            "call": {
                "id": str(call.id),
                "status": call.status,
                "smsTriggered": call.sms_triggered,
                "conversationId": str(call.conversation_id) if call.conversation_id else None,
                "autoResponseSent": call.sms_triggered,
            }
        }, "Missed call processed successfully")
        
    except ValidationError as e:
        logger.warning("Missed call validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404 from service)
        raise e
    except DatabaseError as e:
        logger.error("Database error processing missed call", error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    except ServiceError as e:
        logger.error("Service error processing missed call", error=str(e))
        raise HTTPException(status_code=502, detail="External service error")
    except Exception as e:
        logger.error("Unexpected error processing missed call", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{call_id}", response_model=Dict[str, Any])
async def get_call(
    call_id: UUID,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Get call details by ID."""
    try:
        logger.info("Getting call details", call_id=str(call_id))
        
        call = await call_service.get_call(call_id)
        
        # Verify tenant access
        verify_tenant_access(user_data, call.tenant_id)
        
        return successResponse({
            "call": {
                "id": str(call.id),
                "callSid": call.call_sid,
                "tenantId": str(call.tenant_id),
                "customerPhone": call.customer_phone,
                "businessPhone": call.business_phone,
                "direction": call.direction,
                "status": call.status,
                "startTime": call.start_time.isoformat(),
                "endTime": call.end_time.isoformat() if call.end_time else None,
                "duration": call.duration,
                "conversationId": str(call.conversation_id) if call.conversation_id else None,
                "leadCreated": call.lead_created,
            }
        }, "Call retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404, 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting call", call_id=str(call_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tenant/{tenant_id}/recent")
async def get_recent_calls(
    tenant_id: UUID,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Get recent calls for tenant."""
    try:
        # Verify tenant access
        verify_tenant_access(user_data, tenant_id)
        
        logger.info("Getting recent calls", tenant_id=str(tenant_id))
        
        # This would need to be implemented in the call service
        # For now, return a placeholder response
        return successResponse({
            "calls": [],
            "total": 0,
            "page": 1,
            "pageSize": 50,
        }, "Recent calls retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting recent calls", tenant_id=str(tenant_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")