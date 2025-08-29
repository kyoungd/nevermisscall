"""Lead service for managing lead operations and status tracking."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException

from ..models import (
    Lead,
    LeadCreate,
    LeadUpdate,
    LeadStatusUpdate,
    AIAnalysis,
)
from ..utils import (
    logger,
    query,
    service_client,
    validateRequired,
    DatabaseError,
    ServiceError,
)


class LeadService:
    """Service class for lead operations."""
    
    async def create_lead(self, lead_data: LeadCreate) -> Lead:
        """Create a new lead."""
        validateRequired(lead_data.tenant_id, "tenant_id")
        validateRequired(lead_data.call_id, "call_id")
        validateRequired(lead_data.customer_phone, "customer_phone")
        validateRequired(lead_data.problem_description, "problem_description")
        
        lead_id = uuid4()
        now = datetime.utcnow()
        
        try:
            # Serialize AI analysis if present
            ai_analysis_json = None
            if lead_data.ai_analysis:
                ai_analysis_json = lead_data.ai_analysis.model_dump()
            
            await query(
                """
                INSERT INTO leads (
                    id, tenant_id, conversation_id, call_id, customer_phone,
                    customer_name, customer_email, customer_address,
                    problem_description, job_type, urgency_level, estimated_value,
                    status, status_notes, ai_analysis, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                """,
                [
                    lead_id,
                    lead_data.tenant_id,
                    lead_data.conversation_id,
                    lead_data.call_id,
                    lead_data.customer_phone,
                    lead_data.customer_name,
                    lead_data.customer_email,
                    lead_data.customer_address,
                    lead_data.problem_description,
                    lead_data.job_type,
                    lead_data.urgency_level,
                    lead_data.estimated_value,
                    lead_data.status,
                    None,  # status_notes
                    ai_analysis_json,
                    now,
                    now,
                ]
            )
            
            logger.info(
                "Lead created successfully",
                lead_id=str(lead_id),
                tenant_id=str(lead_data.tenant_id),
                call_id=str(lead_data.call_id)
            )
            
            # Get the created lead
            lead = await self.get_lead(lead_id)
            
            # Broadcast real-time event
            await service_client.broadcast_realtime_event(
                tenant_id=str(lead_data.tenant_id),
                event_type="lead_created",
                event_data={
                    "leadId": str(lead_id),
                    "customerPhone": lead_data.customer_phone,
                    "problemDescription": lead_data.problem_description,
                    "status": lead_data.status,
                    "urgencyLevel": lead_data.urgency_level,
                    "timestamp": now.isoformat(),
                }
            )
            
            return lead
            
        except Exception as e:
            logger.error(
                "Failed to create lead",
                tenant_id=str(lead_data.tenant_id),
                call_id=str(lead_data.call_id),
                error=str(e)
            )
            raise DatabaseError(f"Failed to create lead: {str(e)}")
    
    async def get_lead(self, lead_id: UUID) -> Lead:
        """Get lead by ID."""
        try:
            result = await query(
                "SELECT * FROM leads WHERE id = $1",
                [lead_id]
            )
            
            if not result:
                raise HTTPException(status_code=404, detail="Lead not found")
            
            lead_data = result[0]
            
            # Parse AI analysis if present
            ai_analysis = None
            if lead_data['ai_analysis']:
                ai_analysis = AIAnalysis(**lead_data['ai_analysis'])
            
            return Lead(
                id=lead_data['id'],
                tenant_id=lead_data['tenant_id'],
                conversation_id=lead_data['conversation_id'],
                call_id=lead_data['call_id'],
                customer_phone=lead_data['customer_phone'],
                customer_name=lead_data['customer_name'],
                customer_email=lead_data['customer_email'],
                customer_address=lead_data['customer_address'],
                problem_description=lead_data['problem_description'],
                job_type=lead_data['job_type'],
                urgency_level=lead_data['urgency_level'],
                estimated_value=lead_data['estimated_value'],
                status=lead_data['status'],
                status_notes=lead_data['status_notes'],
                ai_analysis=ai_analysis,
                appointment_id=lead_data['appointment_id'],
                conversion_value=lead_data['conversion_value'],
                lost_reason=lead_data['lost_reason'],
                created_at=lead_data['created_at'],
                updated_at=lead_data['updated_at'],
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get lead", lead_id=str(lead_id), error=str(e))
            raise DatabaseError(f"Failed to get lead: {str(e)}")
    
    async def update_lead(self, lead_id: UUID, update_data: LeadUpdate) -> Lead:
        """Update lead record."""
        try:
            # Build dynamic update query
            set_clauses = []
            values = []
            param_count = 1
            
            update_dict = update_data.model_dump(exclude_unset=True)
            
            for field, value in update_dict.items():
                if field == 'ai_analysis' and value:
                    # Serialize AI analysis
                    value = value.model_dump() if hasattr(value, 'model_dump') else value
                
                set_clauses.append(f"{field} = ${param_count}")
                values.append(value)
                param_count += 1
            
            if not set_clauses:
                return await self.get_lead(lead_id)
            
            # Add updated_at timestamp
            set_clauses.append(f"updated_at = ${param_count}")
            values.append(datetime.utcnow())
            values.append(lead_id)
            
            query_sql = f"""
                UPDATE leads 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count + 1}
            """
            
            await query(query_sql, values)
            
            logger.info("Lead updated successfully", lead_id=str(lead_id))
            
            # Get updated lead
            lead = await self.get_lead(lead_id)
            
            # Broadcast real-time event
            await service_client.broadcast_realtime_event(
                tenant_id=str(lead.tenant_id),
                event_type="lead_updated",
                event_data={
                    "leadId": str(lead_id),
                    "status": lead.status,
                    "estimatedValue": lead.estimated_value,
                    "updatedFields": list(update_dict.keys()),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            
            return lead
            
        except Exception as e:
            logger.error("Failed to update lead", lead_id=str(lead_id), error=str(e))
            raise DatabaseError(f"Failed to update lead: {str(e)}")
    
    async def update_lead_status(
        self, 
        lead_id: UUID, 
        status_update: LeadStatusUpdate,
        user_id: Optional[UUID] = None
    ) -> Lead:
        """Update lead status with notes."""
        logger.info(
            "Updating lead status",
            lead_id=str(lead_id),
            new_status=status_update.status,
            user_id=str(user_id) if user_id else None
        )
        
        update_data = LeadUpdate(
            status=status_update.status,
            status_notes=status_update.notes,
            estimated_value=status_update.estimated_value,
        )
        
        # Add specific fields based on status
        if status_update.status == 'lost' and status_update.notes:
            update_data.lost_reason = status_update.notes
        elif status_update.status == 'completed' and status_update.estimated_value:
            update_data.conversion_value = status_update.estimated_value
        
        lead = await self.update_lead(lead_id, update_data)
        
        # Additional logging for status changes
        logger.info(
            "Lead status updated successfully",
            lead_id=str(lead_id),
            old_status="unknown",  # Would need to track this
            new_status=status_update.status,
            estimated_value=status_update.estimated_value
        )
        
        return lead
    
    async def get_leads_for_tenant(
        self, 
        tenant_id: UUID,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> dict:
        """Get leads for tenant with optional filtering."""
        try:
            offset = (page - 1) * page_size
            
            # Build query based on filters
            where_clauses = ["tenant_id = $1"]
            values = [tenant_id]
            param_count = 2
            
            if status:
                where_clauses.append(f"status = ${param_count}")
                values.append(status)
                param_count += 1
            
            where_clause = " AND ".join(where_clauses)
            
            # Get total count
            count_result = await query(
                f"SELECT COUNT(*) as total FROM leads WHERE {where_clause}",
                values
            )
            total = count_result[0]['total']
            
            # Get paginated results
            values.extend([page_size, offset])
            result = await query(
                f"""
                SELECT * FROM leads 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
                """,
                values
            )
            
            leads = []
            for lead_data in result:
                # Parse AI analysis if present
                ai_analysis = None
                if lead_data['ai_analysis']:
                    ai_analysis = AIAnalysis(**lead_data['ai_analysis'])
                
                leads.append(Lead(
                    id=lead_data['id'],
                    tenant_id=lead_data['tenant_id'],
                    conversation_id=lead_data['conversation_id'],
                    call_id=lead_data['call_id'],
                    customer_phone=lead_data['customer_phone'],
                    customer_name=lead_data['customer_name'],
                    customer_email=lead_data['customer_email'],
                    customer_address=lead_data['customer_address'],
                    problem_description=lead_data['problem_description'],
                    job_type=lead_data['job_type'],
                    urgency_level=lead_data['urgency_level'],
                    estimated_value=lead_data['estimated_value'],
                    status=lead_data['status'],
                    status_notes=lead_data['status_notes'],
                    ai_analysis=ai_analysis,
                    appointment_id=lead_data['appointment_id'],
                    conversion_value=lead_data['conversion_value'],
                    lost_reason=lead_data['lost_reason'],
                    created_at=lead_data['created_at'],
                    updated_at=lead_data['updated_at'],
                ))
            
            return {
                "leads": leads,
                "total": total,
                "page": page,
                "pageSize": page_size,
                "totalPages": (total + page_size - 1) // page_size,
            }
            
        except Exception as e:
            logger.error(
                "Failed to get leads for tenant",
                tenant_id=str(tenant_id),
                status=status,
                error=str(e)
            )
            raise DatabaseError(f"Failed to get leads for tenant: {str(e)}")
    
    async def analyze_lead_with_ai(
        self, 
        lead_id: UUID,
        message_content: str,
        conversation_history: List[str]
    ) -> Lead:
        """Analyze lead using AI and update with results."""
        logger.info("Analyzing lead with AI", lead_id=str(lead_id))
        
        try:
            lead = await self.get_lead(lead_id)
            
            # Get tenant context for AI analysis
            tenant_validation = await service_client.validate_tenant_and_service_area(
                str(lead.tenant_id),
                lead.customer_address
            )
            
            tenant_context = {
                "tenantId": str(lead.tenant_id),
                "businessName": tenant_validation.get('businessName', 'our business'),
                "serviceArea": tenant_validation.get('serviceRadiusMiles', 25),
                "businessHours": tenant_validation.get('businessHours', '07:00-18:00'),
            }
            
            # Process via dispatch-bot-ai
            ai_response = await service_client.process_ai_conversation(
                str(lead.conversation_id),
                message_content,
                conversation_history,
                tenant_context
            )
            
            # Extract AI analysis results
            extracted_info = ai_response.get('extractedInfo', {})
            
            ai_analysis = AIAnalysis(
                confidence=extracted_info.get('jobConfidence', 0.5),
                job_classification=extracted_info.get('jobType', 'unknown'),
                urgency_score=extracted_info.get('urgencyConfidence', 0.5),
                service_area_valid=extracted_info.get('addressVerified', False),
                address_validated=extracted_info.get('addressVerified', False),
            )
            
            # Update lead with AI analysis and extracted information
            update_data = LeadUpdate(
                ai_analysis=ai_analysis,
                job_type=extracted_info.get('jobType'),
                customer_address=extracted_info.get('customerAddress'),
                urgency_level=self._map_urgency_level(extracted_info.get('urgencyLevel', 'normal')),
            )
            
            # Update status if AI indicates high confidence
            if ai_analysis.confidence > 0.8:
                update_data.status = 'qualified'
            
            lead = await self.update_lead(lead_id, update_data)
            
            logger.info(
                "Lead AI analysis completed",
                lead_id=str(lead_id),
                job_type=extracted_info.get('jobType'),
                confidence=ai_analysis.confidence
            )
            
            return lead
            
        except Exception as e:
            logger.error(
                "Failed to analyze lead with AI",
                lead_id=str(lead_id),
                error=str(e)
            )
            # Don't fail the main process if AI analysis fails
            return await self.get_lead(lead_id)
    
    def _map_urgency_level(self, ai_urgency: str) -> str:
        """Map AI urgency levels to lead urgency levels."""
        mapping = {
            'emergency': 'emergency',
            'urgent': 'high',
            'high': 'high',
            'normal': 'normal',
            'low': 'low',
        }
        
        return mapping.get(ai_urgency.lower(), 'normal')


# Global service instance
lead_service = LeadService()