"""Lead controller for handling lead-related API endpoints."""

from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models import LeadStatusUpdate
from ..services import lead_service, validation_service
from ..utils import (
    logger,
    verify_jwt_token,
    verify_tenant_access,
    successResponse,
    errorResponse,
    ValidationError,
    DatabaseError,
    ServiceError,
)

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/{lead_id}", response_model=Dict[str, Any])
async def get_lead(
    lead_id: UUID,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Get lead information by ID."""
    try:
        logger.info("Getting lead details", lead_id=str(lead_id))
        
        lead = await lead_service.get_lead(lead_id)
        
        # Verify tenant access
        verify_tenant_access(user_data, lead.tenant_id)
        
        return successResponse({
            "lead": {
                "id": str(lead.id),
                "tenantId": str(lead.tenant_id),
                "conversationId": str(lead.conversation_id),
                "customerPhone": lead.customer_phone,
                "customerName": lead.customer_name,
                "customerAddress": lead.customer_address,
                "problemDescription": lead.problem_description,
                "urgencyLevel": lead.urgency_level,
                "jobType": lead.job_type,
                "estimatedValue": lead.estimated_value,
                "status": lead.status,
                "aiAnalysis": {
                    "confidence": lead.ai_analysis.confidence,
                    "jobClassification": lead.ai_analysis.job_classification,
                    "urgencyScore": lead.ai_analysis.urgency_score,
                    "serviceAreaValid": lead.ai_analysis.service_area_valid
                } if lead.ai_analysis else None,
                "createdAt": lead.created_at.isoformat(),
            }
        }, "Lead retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404, 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting lead", lead_id=str(lead_id), error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{lead_id}/status", response_model=Dict[str, Any])
async def update_lead_status(
    lead_id: UUID,
    status_update: LeadStatusUpdate,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Update lead status."""
    try:
        logger.info(
            "Updating lead status",
            lead_id=str(lead_id),
            new_status=status_update.status,
            user_id=str(user_data["user_id"])
        )
        
        # Get lead to verify tenant access
        lead = await lead_service.get_lead(lead_id)
        verify_tenant_access(user_data, lead.tenant_id)
        
        # Update lead status
        updated_lead = await lead_service.update_lead_status(
            lead_id, 
            status_update,
            user_data["user_id"]
        )
        
        return successResponse({
            "lead": {
                "id": str(updated_lead.id),
                "status": updated_lead.status,
                "notes": updated_lead.status_notes,
                "estimatedValue": updated_lead.estimated_value,
                "updatedAt": updated_lead.updated_at.isoformat(),
            }
        }, "Lead status updated successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 404, 403)
        raise e
    except ValidationError as e:
        logger.warning("Lead status validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        logger.error("Database error updating lead status", error=str(e))
        raise HTTPException(status_code=500, detail="Database error")
    except Exception as e:
        logger.error("Unexpected error updating lead status", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tenant/{tenant_id}", response_model=Dict[str, Any])
async def get_leads_for_tenant(
    tenant_id: UUID,
    user_data: dict = Depends(verify_jwt_token),
    status: Optional[str] = Query(None, description="Filter by lead status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size")
) -> Dict[str, Any]:
    """Get leads for tenant with optional filtering."""
    try:
        # Verify tenant access
        verify_tenant_access(user_data, tenant_id)
        
        logger.info(
            "Getting leads for tenant",
            tenant_id=str(tenant_id),
            status=status,
            page=page,
            page_size=page_size
        )
        
        result = await lead_service.get_leads_for_tenant(
            tenant_id, status, page, page_size
        )
        
        # Convert leads to serializable format
        leads_data = []
        for lead in result["leads"]:
            leads_data.append({
                "id": str(lead.id),
                "customerPhone": lead.customer_phone,
                "customerName": lead.customer_name,
                "customerAddress": lead.customer_address,
                "problemDescription": lead.problem_description,
                "jobType": lead.job_type,
                "urgencyLevel": lead.urgency_level,
                "estimatedValue": lead.estimated_value,
                "status": lead.status,
                "statusNotes": lead.status_notes,
                "createdAt": lead.created_at.isoformat(),
                "updatedAt": lead.updated_at.isoformat(),
            })
        
        return successResponse({
            "leads": leads_data,
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["pageSize"],
            "totalPages": result["totalPages"],
        }, "Leads retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting leads", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tenant/{tenant_id}/stats", response_model=Dict[str, Any])
async def get_lead_stats(
    tenant_id: UUID,
    user_data: dict = Depends(verify_jwt_token)
) -> Dict[str, Any]:
    """Get lead statistics for tenant."""
    try:
        # Verify tenant access
        verify_tenant_access(user_data, tenant_id)
        
        logger.info("Getting lead stats", tenant_id=str(tenant_id))
        
        # This would need to be implemented in the lead service
        # For now, return placeholder stats
        return successResponse({
            "totalLeads": 0,
            "newLeads": 0,
            "qualifiedLeads": 0,
            "appointmentsScheduled": 0,
            "completedJobs": 0,
            "lostLeads": 0,
            "conversionRate": 0.0,
            "averageValue": 0.0,
        }, "Lead statistics retrieved successfully")
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (like 403)
        raise e
    except Exception as e:
        logger.error("Unexpected error getting lead stats", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")