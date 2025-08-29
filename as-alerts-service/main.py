"""
AS Alerts Service - Simple Alert Management System

A FastAPI-based microservice for managing alerts in the NeverMissCall platform.
Uses the shared library for database, configuration, authentication, and logging.

Port: 3101
Database: PostgreSQL via shared library
Architecture: Single-file implementation using shared utilities
"""

import sys
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
from pathlib import Path

# Add shared library to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'shared'))

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field, field_validator

# Import from shared library
from shared import (
    init_database,
    query,
    health_check,
    logger,
    get_common_config,
    success_response,
    error_response,
    require_service_auth,
    ValidationError,
    NotFoundError
)


# =============================================================================
# Service-Specific Models (Alert-specific extensions)
# =============================================================================

class AlertSeverity(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status workflow"""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertCreate(BaseModel):
    """Model for creating new alerts"""
    tenant_id: str = Field(..., description="Tenant UUID")
    rule_name: str = Field(..., description="Alert rule name")
    message: str = Field(..., description="Alert description")
    severity: AlertSeverity = Field(AlertSeverity.MEDIUM, description="Alert severity")
    
    @field_validator('tenant_id')
    @classmethod
    def validate_tenant_id(cls, v):
        """Validate tenant_id is a valid UUID"""
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            raise ValueError('tenant_id must be a valid UUID')


class AlertUpdate(BaseModel):
    """Model for updating alert status"""
    note: Optional[str] = Field(None, description="Optional note for status change")


class AlertStats(BaseModel):
    """Alert statistics for a tenant"""
    total: int
    triggered: int
    acknowledged: int
    resolved: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    database_connected: bool = True


# =============================================================================
# Database Operations using Shared Library
# =============================================================================

async def create_alert_in_db(alert_data: AlertCreate) -> dict:
    """Create new alert in database using shared library query function"""
    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    try:
        # Insert alert into database
        await query("""
            INSERT INTO alerts (
                id, tenant_id, rule_name, message, severity, status, 
                created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, [alert_id, alert_data.tenant_id, alert_data.rule_name, 
              alert_data.message, alert_data.severity.value, 
              AlertStatus.TRIGGERED.value, now, now])
        
        # Retrieve the created alert
        result = await query("""
            SELECT * FROM alerts WHERE id = $1
        """, [alert_id])
        
        return dict(result[0]) if result else None
        
    except Exception as e:
        logger.error(f"Failed to create alert in database: {e}")
        raise


async def get_alerts_from_db(
    tenant_id: str, 
    status: Optional[str] = None, 
    severity: Optional[str] = None,
    limit: int = 50
) -> List[dict]:
    """Get alerts for tenant with optional filtering using shared library"""
    try:
        # Build dynamic query
        query_sql = "SELECT * FROM alerts WHERE tenant_id = $1"
        params = [tenant_id]
        param_count = 1
        
        if status:
            param_count += 1
            query_sql += f" AND status = ${param_count}"
            params.append(status)
        
        if severity:
            param_count += 1
            query_sql += f" AND severity = ${param_count}"
            params.append(severity)
        
        query_sql += f" ORDER BY created_at DESC LIMIT ${param_count + 1}"
        params.append(limit)
        
        results = await query(query_sql, params)
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Failed to get alerts from database: {e}")
        raise


async def get_alert_by_id(alert_id: str) -> Optional[dict]:
    """Get specific alert by ID using shared library"""
    try:
        # Validate UUID format
        uuid.UUID(alert_id)
    except ValueError:
        return None
    
    try:
        results = await query("SELECT * FROM alerts WHERE id = $1", [alert_id])
        return dict(results[0]) if results else None
        
    except Exception as e:
        logger.error(f"Failed to get alert by ID: {e}")
        raise


async def update_alert_status(
    alert_id: str, 
    new_status: AlertStatus, 
    note: Optional[str] = None
) -> Optional[dict]:
    """Update alert status with optional note using shared library"""
    try:
        now = datetime.now(timezone.utc)
        
        # Prepare status-specific fields
        if new_status == AlertStatus.ACKNOWLEDGED:
            await query("""
                UPDATE alerts 
                SET status = $1, updated_at = $2, acknowledged_at = $3, acknowledgment_note = $4
                WHERE id = $5
            """, [new_status.value, now, now, note, alert_id])
            
        elif new_status == AlertStatus.RESOLVED:
            await query("""
                UPDATE alerts 
                SET status = $1, updated_at = $2, resolved_at = $3, resolution_note = $4
                WHERE id = $5
            """, [new_status.value, now, now, note, alert_id])
        
        # Retrieve updated alert
        results = await query("SELECT * FROM alerts WHERE id = $1", [alert_id])
        return dict(results[0]) if results else None
        
    except Exception as e:
        logger.error(f"Failed to update alert status: {e}")
        raise


async def get_alert_stats_from_db(tenant_id: str) -> AlertStats:
    """Get alert statistics for tenant using shared library"""
    try:
        # Get total count
        total_result = await query(
            "SELECT COUNT(*) as count FROM alerts WHERE tenant_id = $1", 
            [tenant_id]
        )
        total = total_result[0]['count']
        
        # Get counts by status
        triggered_result = await query("""
            SELECT COUNT(*) as count FROM alerts WHERE tenant_id = $1 AND status = 'triggered'
        """, [tenant_id])
        triggered = triggered_result[0]['count']
        
        acknowledged_result = await query("""
            SELECT COUNT(*) as count FROM alerts WHERE tenant_id = $1 AND status = 'acknowledged'
        """, [tenant_id])
        acknowledged = acknowledged_result[0]['count']
        
        resolved_result = await query("""
            SELECT COUNT(*) as count FROM alerts WHERE tenant_id = $1 AND status = 'resolved'
        """, [tenant_id])
        resolved = resolved_result[0]['count']
        
        return AlertStats(
            total=total,
            triggered=triggered,
            acknowledged=acknowledged,
            resolved=resolved
        )
        
    except Exception as e:
        logger.error(f"Failed to get alert statistics: {e}")
        raise


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="AS Alerts Service",
    description="Simple alert management system for NeverMissCall platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
async def startup_event():
    """Initialize using shared library configuration and database"""
    config = get_common_config()
    await init_database(config.database)
    logger.info("AS Alerts Service started on port 3101 using shared library")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources"""
    logger.info("AS Alerts Service shutting down")


# =============================================================================
# Public API Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint using shared library health check"""
    from shared import health_check as shared_health_check
    
    try:
        database_connected = await shared_health_check()
        
        if not database_connected:
            raise HTTPException(status_code=503, detail="Database not available")
        
        return HealthResponse(
            status="healthy",
            service="as-alerts-service",
            database_connected=database_connected
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.post("/alerts", status_code=201)
async def create_alert(alert_data: AlertCreate):
    """Create new alert using shared library patterns"""
    try:
        alert_dict = await create_alert_in_db(alert_data)
        if not alert_dict:
            raise HTTPException(status_code=500, detail="Failed to create alert")
        
        logger.info(f"Created alert {alert_dict['id']} for tenant {alert_dict['tenant_id']}")
        return success_response(alert_dict, "Alert created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        return error_response("Failed to create alert", details={"error": str(e)})


@app.get("/alerts")
async def get_alerts(
    tenant_id: str = Query(..., description="Tenant UUID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity")
):
    """Get alerts for tenant with optional filtering"""
    try:
        # Validate tenant_id
        uuid.UUID(tenant_id)
    except ValueError:
        return error_response("Invalid tenant_id format", details={"field": "tenant_id"})
    
    # Validate status filter
    if status and status not in [s.value for s in AlertStatus]:
        return error_response("Invalid status value", details={"field": "status"})
    
    # Validate severity filter
    if severity and severity not in [s.value for s in AlertSeverity]:
        return error_response("Invalid severity value", details={"field": "severity"})
    
    try:
        alerts = await get_alerts_from_db(tenant_id, status, severity)
        return success_response(alerts, "Alerts retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        return error_response("Failed to retrieve alerts", details={"error": str(e)})


@app.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get specific alert by ID"""
    try:
        alert = await get_alert_by_id(alert_id)
        if not alert:
            return error_response("Alert not found")
        
        return success_response(alert, "Alert retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to get alert: {e}")
        return error_response("Failed to retrieve alert", details={"error": str(e)})


@app.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, update_data: AlertUpdate):
    """Acknowledge alert with optional note"""
    try:
        alert = await update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED, update_data.note)
        if not alert:
            return error_response("Alert not found")
        
        logger.info(f"Acknowledged alert {alert_id}")
        return success_response(alert, "Alert acknowledged successfully")
        
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}")
        return error_response("Failed to acknowledge alert", details={"error": str(e)})


@app.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, update_data: AlertUpdate):
    """Resolve alert with optional note"""
    try:
        alert = await update_alert_status(alert_id, AlertStatus.RESOLVED, update_data.note)
        if not alert:
            return error_response("Alert not found")
        
        logger.info(f"Resolved alert {alert_id}")
        return success_response(alert, "Alert resolved successfully")
        
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}")
        return error_response("Failed to resolve alert", details={"error": str(e)})


@app.get("/stats/{tenant_id}")
async def get_statistics(tenant_id: str):
    """Get alert statistics for tenant"""
    try:
        # Validate tenant_id
        uuid.UUID(tenant_id)
    except ValueError:
        return error_response("Invalid tenant_id format", details={"field": "tenant_id"})
    
    try:
        stats = await get_alert_stats_from_db(tenant_id)
        return success_response(stats.model_dump(), "Statistics retrieved successfully")
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        return error_response("Failed to retrieve statistics", details={"error": str(e)})


# =============================================================================
# Internal Service Endpoints
# =============================================================================

@app.post("/internal/alerts", status_code=201)
async def create_internal_alert(
    alert_data: AlertCreate,
    authenticated: bool = require_service_auth("nmc-internal-services-auth-key-phase1")
):
    """Create alert via internal service-to-service call"""
    try:
        alert_dict = await create_alert_in_db(alert_data)
        if not alert_dict:
            raise HTTPException(status_code=500, detail="Failed to create alert")
        
        logger.info(f"Created internal alert {alert_dict['id']} for tenant {alert_dict['tenant_id']}")
        return success_response(alert_dict, "Internal alert created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create internal alert: {e}")
        return error_response("Failed to create alert", details={"error": str(e)})


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    config = get_common_config()
    from shared import SERVICE_PORTS
    port = SERVICE_PORTS.get('alerts-service', 3101)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )