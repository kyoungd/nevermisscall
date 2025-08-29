"""Call service for managing call operations and business logic."""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..models import (
    Call,
    CallCreate,
    CallUpdate,
    CallWebhook,
    ConversationCreate,
    LeadCreate,
)
from ..utils import (
    logger,
    query,
    service_client,
    validateRequired,
    DatabaseError,
    ServiceError,
)


class CallService:
    """Service class for call operations."""
    
    async def create_call(self, call_data: CallCreate) -> Call:
        """Create a new call record."""
        validateRequired(call_data.call_sid, "call_sid")
        validateRequired(call_data.tenant_id, "tenant_id")
        
        call_id = uuid4()
        now = datetime.utcnow()
        
        try:
            # Insert call record
            await query(
                """
                INSERT INTO calls (
                    id, call_sid, tenant_id, customer_phone, business_phone,
                    direction, status, start_time, caller_city, caller_state,
                    caller_country, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                [
                    call_id,
                    call_data.call_sid,
                    call_data.tenant_id,
                    call_data.customer_phone,
                    call_data.business_phone,
                    call_data.direction,
                    call_data.status,
                    call_data.start_time,
                    call_data.caller_city,
                    call_data.caller_state,
                    call_data.caller_country,
                    now,
                    now,
                ]
            )
            
            logger.info(
                "Call created successfully",
                call_id=str(call_id),
                call_sid=call_data.call_sid,
                tenant_id=str(call_data.tenant_id)
            )
            
            # Return the created call
            return await self.get_call(call_id)
            
        except Exception as e:
            logger.error(
                "Failed to create call",
                call_sid=call_data.call_sid,
                tenant_id=str(call_data.tenant_id),
                error=str(e)
            )
            raise DatabaseError(f"Failed to create call: {str(e)}")
    
    async def get_call(self, call_id: UUID) -> Call:
        """Get call by ID."""
        try:
            result = await query(
                "SELECT * FROM calls WHERE id = $1",
                [call_id]
            )
            
            if not result:
                raise HTTPException(status_code=404, detail="Call not found")
            
            call_data = result[0]
            return Call(
                id=call_data['id'],
                call_sid=call_data['call_sid'],
                tenant_id=call_data['tenant_id'],
                customer_phone=call_data['customer_phone'],
                business_phone=call_data['business_phone'],
                direction=call_data['direction'],
                status=call_data['status'],
                start_time=call_data['start_time'],
                end_time=call_data['end_time'],
                duration=call_data['duration'] or 0,
                processed=call_data['processed'],
                sms_triggered=call_data['sms_triggered'],
                conversation_created=call_data['conversation_created'],
                lead_created=call_data['lead_created'],
                conversation_id=call_data['conversation_id'],
                lead_id=call_data['lead_id'],
                caller_city=call_data['caller_city'],
                caller_state=call_data['caller_state'],
                caller_country=call_data['caller_country'],
                created_at=call_data['created_at'],
                updated_at=call_data['updated_at'],
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get call", call_id=str(call_id), error=str(e))
            raise DatabaseError(f"Failed to get call: {str(e)}")
    
    async def get_call_by_sid(self, call_sid: str) -> Optional[Call]:
        """Get call by Twilio Call SID."""
        try:
            result = await query(
                "SELECT * FROM calls WHERE call_sid = $1",
                [call_sid]
            )
            
            if not result:
                return None
            
            call_data = result[0]
            return Call(
                id=call_data['id'],
                call_sid=call_data['call_sid'],
                tenant_id=call_data['tenant_id'],
                customer_phone=call_data['customer_phone'],
                business_phone=call_data['business_phone'],
                direction=call_data['direction'],
                status=call_data['status'],
                start_time=call_data['start_time'],
                end_time=call_data['end_time'],
                duration=call_data['duration'] or 0,
                processed=call_data['processed'],
                sms_triggered=call_data['sms_triggered'],
                conversation_created=call_data['conversation_created'],
                lead_created=call_data['lead_created'],
                conversation_id=call_data['conversation_id'],
                lead_id=call_data['lead_id'],
                caller_city=call_data['caller_city'],
                caller_state=call_data['caller_state'],
                caller_country=call_data['caller_country'],
                created_at=call_data['created_at'],
                updated_at=call_data['updated_at'],
            )
            
        except Exception as e:
            logger.error("Failed to get call by SID", call_sid=call_sid, error=str(e))
            raise DatabaseError(f"Failed to get call by SID: {str(e)}")
    
    async def update_call(self, call_id: UUID, update_data: CallUpdate) -> Call:
        """Update call record."""
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
                return await self.get_call(call_id)
            
            # Add updated_at timestamp
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            values.append(call_id)
            
            query_sql = f"""
                UPDATE calls 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count + 1}
            """
            
            await query(query_sql, values)
            
            logger.info("Call updated successfully", call_id=str(call_id))
            return await self.get_call(call_id)
            
        except Exception as e:
            logger.error("Failed to update call", call_id=str(call_id), error=str(e))
            raise DatabaseError(f"Failed to update call: {str(e)}")
    
    async def process_incoming_call(self, webhook_data: CallWebhook) -> Call:
        """Process incoming call webhook from Twilio."""
        logger.info(
            "Processing incoming call",
            call_sid=webhook_data.callSid,
            from_phone=webhook_data.from_,
            to_phone=webhook_data.to
        )
        
        # Check if call already exists
        existing_call = await self.get_call_by_sid(webhook_data.callSid)
        if existing_call:
            logger.info("Call already exists", call_sid=webhook_data.callSid)
            return existing_call
        
        # Create new call record
        call_data = CallCreate(
            call_sid=webhook_data.callSid,
            tenant_id=webhook_data.tenant_id,
            customer_phone=webhook_data.from_,
            business_phone=webhook_data.to,
            direction='inbound' if webhook_data.direction.lower() == 'inbound' else 'outbound',
            status=webhook_data.call_status.replace('-', '_'),
            start_time=webhook_data.timestamp or datetime.utcnow(),
        )
        
        call = await self.create_call(call_data)
        
        # Broadcast real-time event
        await service_client.broadcast_realtime_event(
            tenant_id=str(call.tenant_id),
            event_type="call_incoming",
            event_data={
                "callId": str(call.id),
                "customerPhone": call.customer_phone,
                "status": call.status,
                "timestamp": call.start_time.isoformat(),
            }
        )
        
        return call
    
    async def process_missed_call(self, call_sid: str, webhook_data: dict) -> Call:
        """Process missed call and trigger SMS workflow."""
        logger.info("Processing missed call", call_sid=call_sid)
        
        # Get existing call
        call = await self.get_call_by_sid(call_sid)
        if not call:
            raise HTTPException(status_code=404, detail="Call not found")
        
        # Update call status
        update_data = CallUpdate(
            status='missed',
            end_time=webhook_data.get('endTime', datetime.utcnow()),
            duration=webhook_data.get('callDuration', 0),
            processed=True,
        )
        
        call = await self.update_call(call.id, update_data)
        
        # Create conversation and lead in parallel
        conversation_task = self._create_conversation_for_missed_call(call)
        lead_task = self._create_lead_for_missed_call(call)
        
        conversation, lead = await asyncio.gather(conversation_task, lead_task)
        
        # Update call with conversation and lead IDs
        update_data = CallUpdate(
            conversation_id=conversation.id,
            lead_id=lead.id,
            conversation_created=True,
            lead_created=True,
        )
        
        call = await self.update_call(call.id, update_data)
        
        # Send auto-response SMS
        await self._send_auto_response_sms(call, conversation)
        
        # Update call to mark SMS as triggered
        update_data = CallUpdate(sms_triggered=True)
        call = await self.update_call(call.id, update_data)
        
        # Broadcast real-time event
        await service_client.broadcast_realtime_event(
            tenant_id=str(call.tenant_id),
            event_type="call_missed",
            event_data={
                "callId": str(call.id),
                "conversationId": str(conversation.id),
                "leadId": str(lead.id),
                "customerPhone": call.customer_phone,
                "autoResponseSent": True,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        
        logger.info(
            "Missed call processed successfully",
            call_id=str(call.id),
            conversation_id=str(conversation.id),
            lead_id=str(lead.id)
        )
        
        return call
    
    async def _create_conversation_for_missed_call(self, call: Call):
        """Create conversation for missed call."""
        from .conversation_service import ConversationService
        
        conversation_service = ConversationService()
        conversation_data = ConversationCreate(
            tenant_id=call.tenant_id,
            call_id=call.id,
            customer_phone=call.customer_phone,
            business_phone=call.business_phone,
        )
        
        return await conversation_service.create_conversation(conversation_data)
    
    async def _create_lead_for_missed_call(self, call: Call):
        """Create lead for missed call."""
        from .lead_service import LeadService
        
        lead_service = LeadService()
        lead_data = LeadCreate(
            tenant_id=call.tenant_id,
            conversation_id=uuid4(),  # Will be updated later
            call_id=call.id,
            customer_phone=call.customer_phone,
            problem_description=f"Missed call from {call.customer_phone}",
            urgency_level='normal',
            status='new',
        )
        
        return await lead_service.create_lead(lead_data)
    
    async def _send_auto_response_sms(self, call: Call, conversation):
        """Send auto-response SMS for missed call."""
        try:
            # Get tenant information to customize message
            tenant_validation = await service_client.validate_tenant_and_service_area(
                str(call.tenant_id)
            )
            
            business_name = tenant_validation.get('businessName', 'our business')
            
            message = f"Hi! Sorry we missed your call at {business_name}. How can we help you today? Please reply with details about what you need."
            
            # Send SMS via twilio-server
            await service_client.send_sms_via_twilio_server(
                to_phone=call.customer_phone,
                from_phone=call.business_phone,
                message=message,
                tenant_id=str(call.tenant_id),
            )
            
            logger.info(
                "Auto-response SMS sent",
                call_id=str(call.id),
                conversation_id=str(conversation.id),
                to_phone=call.customer_phone
            )
            
        except Exception as e:
            logger.error(
                "Failed to send auto-response SMS",
                call_id=str(call.id),
                error=str(e)
            )
            # Don't raise exception as this shouldn't fail the main process
            raise ServiceError(f"Failed to send auto-response SMS: {str(e)}")


# Global service instance
call_service = CallService()