"""Conversation controller for handling conversation-related API endpoints."""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    ConversationReplyRequest,
    MessageWebhook,
)
from ..services import conversation_service, validation_service
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

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{conversation_id}/messages", response_model=Dict[str, Any])
async def process_incoming_message(
    conversation_id: UUID,
    message_data: Dict[str, Any],
    _: str = Depends(verify_internal_service_key)
) -> Dict[str, Any]:
    """Process incoming SMS message for conversation."""
    try:
        message_sid = message_data.get("messageSid")
        message_body = message_data.get("body")
        
        if not message_sid or not message_body:
            raise ValidationError("messageSid and body are required")
        
        # Validate message content
        if not validation_service.validate_message_content(message_body):
            raise ValidationError("Invalid message content")
        
        logger.info(
            "Processing incoming message",
            conversation_id=str(conversation_id),
            message_sid=message_sid
        )
        
        result = await conversation_service.process_incoming_message(
            conversation_id, message_body, message_sid
        )
        
        return successResponse(result, "Message processed successfully")
        
    except ValidationError as e:
        logger.warning("Message validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404 from service)
        raise e
    except DatabaseError as e:
        logger.error("Database error processing message", error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    except ServiceError as e:
        logger.error("Service error processing message", error=str(e))
        raise HTTPException(status_code=502, detail="External service error")
    except Exception as e:
        logger.error("Unexpected error processing message", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{conversation_id}/reply", response_model=Dict[str, Any])
async def send_human_reply(
    conversation_id: UUID,
    reply_data: ConversationReplyRequest,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Send human response to conversation (owner takeover)."""
    try:
        # Validate message content
        if not validation_service.validate_message_content(reply_data.message):
            raise ValidationError("Invalid message content")
        
        logger.info(
            "Sending human reply",
            conversation_id=str(conversation_id),
            user_id=str(user_data["user_id"])
        )
        
        # Get conversation to verify tenant access
        conversation = await conversation_service.get_conversation(conversation_id)
        verify_tenant_access(user_data, conversation.tenant_id)
        
        result = await conversation_service.send_human_reply(
            conversation_id,
            reply_data.message,
            user_data["user_id"]
        )
        
        return successResponse(result, "Human reply sent successfully")
        
    except ValidationError as e:
        logger.warning("Reply validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404, 403)
        raise e
    except DatabaseError as e:
        logger.error("Database error sending reply", error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    except ServiceError as e:
        logger.error("Service error sending reply", error=str(e))
        raise HTTPException(status_code=502, detail="External service error")
    except Exception as e:
        logger.error("Unexpected error sending reply", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{conversation_id}", response_model=Dict[str, Any])
async def get_conversation(
    conversation_id: UUID,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Get conversation details and message history."""
    try:
        logger.info("Getting conversation details", conversation_id=str(conversation_id))
        
        conversation = await conversation_service.get_conversation(conversation_id)
        
        # Verify tenant access
        verify_tenant_access(user_data, conversation.tenant_id)
        
        # Get messages
        messages = await conversation_service.get_conversation_messages(conversation_id)
        
        return successResponse({
            "conversation": {
                "id": str(conversation.id),
                "tenantId": str(conversation.tenant_id),
                "customerPhone": conversation.customer_phone,
                "businessPhone": conversation.business_phone,
                "status": conversation.status,
                "aiActive": conversation.ai_active,
                "humanTakeoverAt": conversation.human_takeover_time.isoformat() if conversation.human_takeover_time else None,
                "lastMessageAt": conversation.last_message_time.isoformat(),
                "messageCount": conversation.message_count,
                "leadId": str(conversation.lead_id) if conversation.lead_id else None,
                "createdAt": conversation.created_at.isoformat(),
            },
            "messages": [
                {
                    "id": str(msg.id),
                    "direction": msg.direction,
                    "body": msg.body,
                    "sender": msg.sender,
                    "timestamp": msg.sent_at.isoformat(),
                } for msg in messages
            ]
        }, "Conversation retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404, 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting conversation", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tenant/{tenant_id}/active", response_model=Dict[str, Any])
async def get_active_conversations(
    tenant_id: UUID,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Get all active conversations for a tenant."""
    try:
        # Verify tenant access
        verify_tenant_access(user_data, tenant_id)
        
        logger.info("Getting active conversations", tenant_id=str(tenant_id))
        
        result = await conversation_service.get_active_conversations_for_tenant(tenant_id)
        
        # Convert conversations to serializable format
        conversations_data = []
        for conv in result["conversations"]:
            conversations_data.append({
                "id": str(conv.id),
                "customerPhone": conv.customer_phone,
                "status": conv.status,
                "aiActive": conv.ai_active,
                "lastMessage": conv.last_message,
                "lastMessageAt": conv.last_message_at.isoformat(),
                "messageCount": conv.message_count,
                "leadStatus": conv.lead_status,
            })
        
        return successResponse({
            "conversations": conversations_data,
            "totalActive": result["totalActive"],
            "aiHandledCount": result["aiHandledCount"],
            "humanHandledCount": result["humanHandledCount"],
        }, "Active conversations retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting active conversations", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{conversation_id}/ai/process", response_model=Dict[str, Any])
async def trigger_ai_processing(
    conversation_id: UUID,
    ai_request: Dict[str, Any],
    _: str = Depends(verify_internal_service_key)
) -> Dict[str, Any]:
    """Trigger AI processing of conversation (internal endpoint)."""
    try:
        message_content = ai_request.get("messageContent")
        conversation_history = ai_request.get("conversationHistory", [])
        tenant_context = ai_request.get("tenantContext", {})
        
        if not message_content:
            raise ValidationError("messageContent is required")
        
        logger.info(
            "Triggering AI processing",
            conversation_id=str(conversation_id)
        )
        
        # This would integrate with the AI processing logic
        # For now, return a placeholder response
        return successResponse({
            "aiResponse": {
                "message": "I can help with that! Let me check availability...",
                "confidence": 0.85,
                "intent": "schedule_service",
                "extractedInfo": {
                    "jobType": "faucet_repair",
                    "urgency": "normal"
                },
                "nextAction": "schedule_appointment"
            }
        }, "AI processing completed")
        
    except ValidationError as e:
        logger.warning("AI processing validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error in AI processing", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{conversation_id}/ai/deactivate", response_model=Dict[str, Any])
async def deactivate_ai(
    conversation_id: UUID,
    deactivation_data: Dict[str, Any],
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Deactivate AI for human takeover."""
    try:
        logger.info(
            "Deactivating AI for conversation",
            conversation_id=str(conversation_id),
            user_id=str(user_data["user_id"])
        )
        
        # Get conversation to verify tenant access
        conversation = await conversation_service.get_conversation(conversation_id)
        verify_tenant_access(user_data, conversation.tenant_id)
        
        # Update conversation to deactivate AI
        from ..models import ConversationUpdate
        from datetime import datetime
        
        update_data = ConversationUpdate(
            ai_active=False,
            human_active=True,
            human_takeover_time=datetime.utcnow(),
        )
        
        updated_conversation = await conversation_service.update_conversation(
            conversation_id, update_data
        )
        
        return successResponse({
            "conversation": {
                "id": str(updated_conversation.id),
                "aiActive": updated_conversation.ai_active,
                "humanActive": updated_conversation.human_active,
                "takeoverAt": updated_conversation.human_takeover_time.isoformat() if updated_conversation.human_takeover_time else None,
                "takeoverBy": str(user_data["user_id"]),
            }
        }, "AI deactivated successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404, 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error deactivating AI", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")