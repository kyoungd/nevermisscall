"""Conversation service for managing conversation operations and AI coordination."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..models import (
    Conversation,
    ConversationCreate,
    ConversationUpdate,
    ConversationSummary,
    Message,
    MessageCreate,
    MessageUpdate,
)
from ..utils import (
    logger,
    query,
    service_client,
    validateRequired,
    DatabaseError,
    ServiceError,
)
from ..config import settings


class ConversationService:
    """Service class for conversation operations."""
    
    async def create_conversation(self, conversation_data: ConversationCreate) -> Conversation:
        """Create a new conversation."""
        validateRequired(conversation_data.tenant_id, "tenant_id")
        validateRequired(conversation_data.call_id, "call_id")
        
        conversation_id = uuid4()
        now = datetime.utcnow()
        
        try:
            await query(
                """
                INSERT INTO conversations (
                    id, tenant_id, call_id, customer_phone, business_phone,
                    status, ai_active, human_active, last_message_time,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                [
                    conversation_id,
                    conversation_data.tenant_id,
                    conversation_data.call_id,
                    conversation_data.customer_phone,
                    conversation_data.business_phone,
                    conversation_data.status,
                    False,  # ai_active
                    False,  # human_active
                    now,    # last_message_time
                    now,    # created_at
                    now,    # updated_at
                ]
            )
            
            logger.info(
                "Conversation created successfully",
                conversation_id=str(conversation_id),
                tenant_id=str(conversation_data.tenant_id),
                call_id=str(conversation_data.call_id)
            )
            
            return await self.get_conversation(conversation_id)
            
        except Exception as e:
            logger.error(
                "Failed to create conversation",
                tenant_id=str(conversation_data.tenant_id),
                call_id=str(conversation_data.call_id),
                error=str(e)
            )
            raise DatabaseError(f"Failed to create conversation: {str(e)}")
    
    async def get_conversation(self, conversation_id: UUID) -> Conversation:
        """Get conversation by ID."""
        try:
            result = await query(
                "SELECT * FROM conversations WHERE id = $1",
                [conversation_id]
            )
            
            if not result:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            conv_data = result[0]
            return Conversation(
                id=conv_data['id'],
                tenant_id=conv_data['tenant_id'],
                call_id=conv_data['call_id'],
                customer_phone=conv_data['customer_phone'],
                business_phone=conv_data['business_phone'],
                status=conv_data['status'],
                ai_active=conv_data['ai_active'],
                human_active=conv_data['human_active'],
                ai_handoff_time=conv_data['ai_handoff_time'],
                human_takeover_time=conv_data['human_takeover_time'],
                last_message_time=conv_data['last_message_time'],
                last_human_response_time=conv_data['last_human_response_time'],
                message_count=conv_data['message_count'],
                ai_message_count=conv_data['ai_message_count'],
                human_message_count=conv_data['human_message_count'],
                appointment_scheduled=conv_data['appointment_scheduled'],
                outcome=conv_data['outcome'],
                lead_id=conv_data['lead_id'],
                created_at=conv_data['created_at'],
                updated_at=conv_data['updated_at'],
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get conversation", conversation_id=str(conversation_id), error=str(e))
            raise DatabaseError(f"Failed to get conversation: {str(e)}")
    
    async def update_conversation(self, conversation_id: UUID, update_data: ConversationUpdate) -> Conversation:
        """Update conversation record."""
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            
            for field, value in update_data.model_dump(exclude_unset=True).items():
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            
            if not set_clauses:
                return await self.get_conversation(conversation_id)
            
            # Add updated_at timestamp
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            values.append(conversation_id)
            
            query_sql = f"""
                UPDATE conversations 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count + 1}
            """
            
            await query(query_sql, values)
            
            logger.info("Conversation updated successfully", conversation_id=str(conversation_id))
            return await self.get_conversation(conversation_id)
            
        except Exception as e:
            logger.error("Failed to update conversation", conversation_id=str(conversation_id), error=str(e))
            raise DatabaseError(f"Failed to update conversation: {str(e)}")
    
    async def add_message(self, message_data: MessageCreate) -> Message:
        """Add message to conversation."""
        validateRequired(message_data.conversation_id, "conversation_id")
        validateRequired(message_data.body, "body")
        
        message_id = uuid4()
        now = datetime.utcnow()
        sent_at = message_data.sent_at or now
        
        try:
            # Insert message
            await query(
                """
                INSERT INTO messages (
                    id, conversation_id, tenant_id, direction, sender, body,
                    message_sid, processed, ai_processed, status,
                    sent_at, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                [
                    message_id,
                    message_data.conversation_id,
                    message_data.tenant_id,
                    message_data.direction,
                    message_data.sender,
                    message_data.body,
                    message_data.message_sid,
                    False,  # processed
                    False,  # ai_processed
                    'sent', # status
                    sent_at,
                    now,
                ]
            )
            
            # Update conversation message counts and last message time
            await self._update_conversation_message_stats(
                message_data.conversation_id,
                message_data.sender,
                sent_at
            )
            
            logger.info(
                "Message added successfully",
                message_id=str(message_id),
                conversation_id=str(message_data.conversation_id),
                direction=message_data.direction,
                sender=message_data.sender
            )
            
            # Get the created message
            result = await query("SELECT * FROM messages WHERE id = $1", [message_id])
            msg_data = result[0]
            
            return Message(
                id=msg_data['id'],
                conversation_id=msg_data['conversation_id'],
                tenant_id=msg_data['tenant_id'],
                direction=msg_data['direction'],
                sender=msg_data['sender'],
                body=msg_data['body'],
                message_sid=msg_data['message_sid'],
                processed=msg_data['processed'],
                ai_processed=msg_data['ai_processed'],
                confidence=msg_data['confidence'],
                intent=msg_data['intent'],
                status=msg_data['status'],
                error_code=msg_data['error_code'],
                error_message=msg_data['error_message'],
                sent_at=msg_data['sent_at'],
                delivered_at=msg_data['delivered_at'],
                created_at=msg_data['created_at'],
            )
            
        except Exception as e:
            logger.error(
                "Failed to add message",
                conversation_id=str(message_data.conversation_id),
                error=str(e)
            )
            raise DatabaseError(f"Failed to add message: {str(e)}")
    
    async def get_conversation_messages(self, conversation_id: UUID) -> List[Message]:
        """Get all messages for a conversation."""
        try:
            result = await query(
                """
                SELECT * FROM messages 
                WHERE conversation_id = $1 
                ORDER BY created_at ASC
                """,
                [conversation_id]
            )
            
            messages = []
            for msg_data in result:
                messages.append(Message(
                    id=msg_data['id'],
                    conversation_id=msg_data['conversation_id'],
                    tenant_id=msg_data['tenant_id'],
                    direction=msg_data['direction'],
                    sender=msg_data['sender'],
                    body=msg_data['body'],
                    message_sid=msg_data['message_sid'],
                    processed=msg_data['processed'],
                    ai_processed=msg_data['ai_processed'],
                    confidence=msg_data['confidence'],
                    intent=msg_data['intent'],
                    status=msg_data['status'],
                    error_code=msg_data['error_code'],
                    error_message=msg_data['error_message'],
                    sent_at=msg_data['sent_at'],
                    delivered_at=msg_data['delivered_at'],
                    created_at=msg_data['created_at'],
                ))
            
            return messages
            
        except Exception as e:
            logger.error("Failed to get conversation messages", conversation_id=str(conversation_id), error=str(e))
            raise DatabaseError(f"Failed to get conversation messages: {str(e)}")
    
    async def process_incoming_message(self, conversation_id: UUID, message_body: str, message_sid: str) -> dict:
        """Process incoming SMS message and trigger AI if needed."""
        logger.info(
            "Processing incoming message",
            conversation_id=str(conversation_id),
            message_sid=message_sid
        )
        
        # Get conversation
        conversation = await self.get_conversation(conversation_id)
        
        # Add incoming message
        message_data = MessageCreate(
            conversation_id=conversation_id,
            tenant_id=conversation.tenant_id,
            direction='inbound',
            sender='customer',
            body=message_body,
            message_sid=message_sid,
        )
        
        message = await self.add_message(message_data)
        
        # Start AI takeover timer if not already active and human not active
        ai_processing_triggered = False
        human_response_window = None
        
        if not conversation.ai_active and not conversation.human_active:
            # Start timer for AI activation
            human_response_window = settings.ai_takeover_delay_seconds
            
            # Schedule AI activation
            asyncio.create_task(
                self._schedule_ai_activation(conversation_id, settings.ai_takeover_delay_seconds)
            )
            
            logger.info(
                "AI takeover timer started",
                conversation_id=str(conversation_id),
                delay_seconds=settings.ai_takeover_delay_seconds
            )
        elif conversation.ai_active:
            # If AI is active, process immediately
            ai_processing_triggered = True
            await self._trigger_ai_processing(conversation_id, message_body)
        
        # Broadcast real-time event
        await service_client.broadcast_realtime_event(
            tenant_id=str(conversation.tenant_id),
            event_type="message_received",
            event_data={
                "conversationId": str(conversation_id),
                "messageId": str(message.id),
                "customerPhone": conversation.customer_phone,
                "messageBody": message_body,
                "aiActive": conversation.ai_active,
                "humanActive": conversation.human_active,
                "timestamp": message.sent_at.isoformat(),
            }
        )
        
        return {
            "id": str(message.id),
            "conversationId": str(conversation_id),
            "direction": message.direction,
            "processed": True,
            "aiProcessingTriggered": ai_processing_triggered,
            "humanResponseWindow": human_response_window,
        }
    
    async def send_human_reply(self, conversation_id: UUID, message: str, user_id: UUID) -> dict:
        """Send human reply and deactivate AI."""
        logger.info(
            "Sending human reply",
            conversation_id=str(conversation_id),
            user_id=str(user_id)
        )
        
        conversation = await self.get_conversation(conversation_id)
        
        # Deactivate AI and activate human
        update_data = ConversationUpdate(
            ai_active=False,
            human_active=True,
            human_takeover_time=datetime.utcnow(),
            last_human_response_time=datetime.utcnow(),
        )
        
        await self.update_conversation(conversation_id, update_data)
        
        # Add outbound message
        message_data = MessageCreate(
            conversation_id=conversation_id,
            tenant_id=conversation.tenant_id,
            direction='outbound',
            sender='human',
            body=message,
        )
        
        reply_message = await self.add_message(message_data)
        
        # Send SMS via twilio-server
        sms_response = await service_client.send_sms_via_twilio_server(
            to_phone=conversation.customer_phone,
            from_phone=conversation.business_phone,
            message=message,
            tenant_id=str(conversation.tenant_id),
        )
        
        # Update message with Twilio SID if available
        if sms_response.get('messageSid'):
            message_update = MessageUpdate(message_sid=sms_response['messageSid'])
            await query(
                "UPDATE messages SET message_sid = $1 WHERE id = $2",
                [sms_response['messageSid'], reply_message.id]
            )
        
        # Broadcast real-time event
        await service_client.broadcast_realtime_event(
            tenant_id=str(conversation.tenant_id),
            event_type="human_reply_sent",
            event_data={
                "conversationId": str(conversation_id),
                "messageId": str(reply_message.id),
                "userId": str(user_id),
                "messageBody": message,
                "aiDeactivated": True,
                "timestamp": reply_message.sent_at.isoformat(),
            }
        )
        
        logger.info(
            "Human reply sent successfully",
            conversation_id=str(conversation_id),
            message_id=str(reply_message.id)
        )
        
        return {
            "id": str(reply_message.id),
            "conversationId": str(conversation_id),
            "direction": "outbound",
            "sender": "human",
            "messageSid": sms_response.get('messageSid'),
            "aiDeactivated": True,
            "sentAt": reply_message.sent_at.isoformat(),
        }
    
    async def get_active_conversations_for_tenant(self, tenant_id: UUID) -> dict:
        """Get all active conversations for a tenant."""
        try:
            result = await query(
                """
                SELECT c.*, 
                       m.body as last_message,
                       l.status as lead_status
                FROM conversations c
                LEFT JOIN messages m ON m.id = (
                    SELECT id FROM messages 
                    WHERE conversation_id = c.id 
                    ORDER BY created_at DESC 
                    LIMIT 1
                )
                LEFT JOIN leads l ON l.conversation_id = c.id
                WHERE c.tenant_id = $1 AND c.status = 'active'
                ORDER BY c.last_message_time DESC
                """,
                [tenant_id]
            )
            
            conversations = []
            ai_handled_count = 0
            human_handled_count = 0
            
            for conv_data in result:
                if conv_data['ai_active']:
                    ai_handled_count += 1
                if conv_data['human_active']:
                    human_handled_count += 1
                
                conversations.append(ConversationSummary(
                    id=conv_data['id'],
                    customer_phone=conv_data['customer_phone'],
                    status=conv_data['status'],
                    ai_active=conv_data['ai_active'],
                    last_message=conv_data['last_message'],
                    last_message_at=conv_data['last_message_time'],
                    message_count=conv_data['message_count'],
                    lead_status=conv_data['lead_status'],
                ))
            
            return {
                "conversations": conversations,
                "totalActive": len(conversations),
                "aiHandledCount": ai_handled_count,
                "humanHandledCount": human_handled_count,
            }
            
        except Exception as e:
            logger.error(
                "Failed to get active conversations",
                tenant_id=str(tenant_id),
                error=str(e)
            )
            raise DatabaseError(f"Failed to get active conversations: {str(e)}")
    
    async def _update_conversation_message_stats(self, conversation_id: UUID, sender: str, message_time: datetime):
        """Update conversation message statistics."""
        try:
            # Increment appropriate counters
            if sender == 'ai':
                await query(
                    """
                    UPDATE conversations 
                    SET message_count = message_count + 1,
                        ai_message_count = ai_message_count + 1,
                        last_message_time = $2,
                        updated_at = $3
                    WHERE id = $1
                    """,
                    [conversation_id, message_time, datetime.utcnow()]
                )
            elif sender == 'human':
                await query(
                    """
                    UPDATE conversations 
                    SET message_count = message_count + 1,
                        human_message_count = human_message_count + 1,
                        last_message_time = $2,
                        last_human_response_time = $2,
                        updated_at = $3
                    WHERE id = $1
                    """,
                    [conversation_id, message_time, datetime.utcnow()]
                )
            else:
                await query(
                    """
                    UPDATE conversations 
                    SET message_count = message_count + 1,
                        last_message_time = $2,
                        updated_at = $3
                    WHERE id = $1
                    """,
                    [conversation_id, message_time, datetime.utcnow()]
                )
                
        except Exception as e:
            logger.error(
                "Failed to update conversation stats",
                conversation_id=str(conversation_id),
                error=str(e)
            )
            # Don't raise exception as this is a supporting operation
    
    async def _schedule_ai_activation(self, conversation_id: UUID, delay_seconds: int):
        """Schedule AI activation after delay."""
        await asyncio.sleep(delay_seconds)
        
        try:
            # Check if human has responded during the delay
            conversation = await self.get_conversation(conversation_id)
            
            if conversation.human_active or conversation.ai_active:
                logger.info(
                    "AI activation cancelled - human or AI already active",
                    conversation_id=str(conversation_id)
                )
                return
            
            # Activate AI
            update_data = ConversationUpdate(
                ai_active=True,
                ai_handoff_time=datetime.utcnow(),
            )
            
            await self.update_conversation(conversation_id, update_data)
            
            # Get latest message to trigger AI processing
            messages = await self.get_conversation_messages(conversation_id)
            if messages:
                latest_message = messages[-1]
                await self._trigger_ai_processing(conversation_id, latest_message.body)
            
            logger.info(
                "AI activated successfully",
                conversation_id=str(conversation_id)
            )
            
        except Exception as e:
            logger.error(
                "Failed to activate AI",
                conversation_id=str(conversation_id),
                error=str(e)
            )
    
    async def _trigger_ai_processing(self, conversation_id: UUID, message_content: str):
        """Trigger AI processing for conversation."""
        try:
            conversation = await self.get_conversation(conversation_id)
            messages = await self.get_conversation_messages(conversation_id)
            
            # Build conversation history
            conversation_history = []
            for msg in messages[:-1]:  # Exclude current message
                conversation_history.append(msg.body)
            
            # Get tenant context
            tenant_validation = await service_client.validate_tenant_and_service_area(
                str(conversation.tenant_id)
            )
            
            tenant_context = {
                "tenantId": str(conversation.tenant_id),
                "businessName": tenant_validation.get('businessName', 'our business'),
                "serviceArea": tenant_validation.get('serviceRadiusMiles', 25),
                "businessHours": tenant_validation.get('businessHours', '07:00-18:00'),
            }
            
            # Process via dispatch-bot-ai
            ai_response = await service_client.process_ai_conversation(
                str(conversation_id),
                message_content,
                conversation_history,
                tenant_context
            )
            
            # If AI generated a response, add it as outbound message
            if ai_response.get('aiResponse', {}).get('message'):
                ai_message = ai_response['aiResponse']['message']
                
                message_data = MessageCreate(
                    conversation_id=conversation_id,
                    tenant_id=conversation.tenant_id,
                    direction='outbound',
                    sender='ai',
                    body=ai_message,
                )
                
                ai_reply = await self.add_message(message_data)
                
                # Send SMS via twilio-server
                sms_response = await service_client.send_sms_via_twilio_server(
                    to_phone=conversation.customer_phone,
                    from_phone=conversation.business_phone,
                    message=ai_message,
                    tenant_id=str(conversation.tenant_id),
                )
                
                # Update message with Twilio SID
                if sms_response.get('messageSid'):
                    await query(
                        "UPDATE messages SET message_sid = $1 WHERE id = $2",
                        [sms_response['messageSid'], ai_reply.id]
                    )
                
                logger.info(
                    "AI response sent successfully",
                    conversation_id=str(conversation_id),
                    ai_message_id=str(ai_reply.id)
                )
            
        except Exception as e:
            logger.error(
                "Failed to trigger AI processing",
                conversation_id=str(conversation_id),
                error=str(e)
            )


# Global service instance
conversation_service = ConversationService()