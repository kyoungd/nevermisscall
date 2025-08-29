"""Redis client for metrics storage and caching."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aioredis
from ..config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for health metrics and service state."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
    
    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        try:
            self.redis = aioredis.from_url(
                settings.redis_url,
                db=settings.metrics_redis_db,
                decode_responses=True
            )
            
            # Test connection
            await self.redis.ping()
            logger.info(f"Redis connection initialized on database {settings.metrics_redis_db}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def store_health_check(self, service_name: str, result: Dict[str, Any]) -> bool:
        """Store health check result."""
        try:
            key = f"health:{service_name}"
            
            # Store the latest result
            await self.redis.hset(key, mapping={
                "status": result["status"],
                "response_time": result["response_time"],
                "timestamp": result["timestamp"],
                "http_status": result.get("http_status", 0),
                "error_message": result.get("error_message", ""),
                "consecutive_failures": result.get("consecutive_failures", 0),
                "consecutive_successes": result.get("consecutive_successes", 0)
            })
            
            # Set TTL
            await self.redis.expire(key, settings.health_data_ttl_seconds)
            
            # Store in history (limited to last 100 checks)
            history_key = f"health:history:{service_name}"
            await self.redis.lpush(history_key, json.dumps(result))
            await self.redis.ltrim(history_key, 0, 99)  # Keep only last 100
            await self.redis.expire(history_key, settings.health_data_ttl_seconds)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store health check for {service_name}: {e}")
            return False
    
    async def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get latest health status for a service."""
        try:
            key = f"health:{service_name}"
            data = await self.redis.hgetall(key)
            
            if not data:
                return None
                
            # Convert types
            return {
                "name": service_name,
                "status": data.get("status", "unknown"),
                "response_time": int(data.get("response_time", 0)),
                "timestamp": data.get("timestamp"),
                "http_status": int(data.get("http_status", 0)),
                "error_message": data.get("error_message"),
                "consecutive_failures": int(data.get("consecutive_failures", 0)),
                "consecutive_successes": int(data.get("consecutive_successes", 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get health for {service_name}: {e}")
            return None
    
    async def get_service_health_history(self, service_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get health check history for a service."""
        try:
            history_key = f"health:history:{service_name}"
            history_data = await self.redis.lrange(history_key, 0, limit - 1)
            
            history = []
            for entry in history_data:
                try:
                    history.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
                    
            return history
            
        except Exception as e:
            logger.error(f"Failed to get health history for {service_name}: {e}")
            return []
    
    async def store_service_metrics(self, service_name: str, metrics: Dict[str, Any]) -> bool:
        """Store service performance metrics."""
        try:
            key = f"metrics:{service_name}"
            
            # Store current metrics
            metrics_data = {
                "timestamp": datetime.utcnow().isoformat(),
                **metrics
            }
            
            await self.redis.hset(key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in metrics_data.items()
            })
            
            await self.redis.expire(key, settings.health_data_ttl_seconds)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store metrics for {service_name}: {e}")
            return False
    
    async def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service performance metrics."""
        try:
            key = f"metrics:{service_name}"
            data = await self.redis.hgetall(key)
            
            if not data:
                return None
                
            # Parse JSON fields
            parsed_data = {}
            for k, v in data.items():
                try:
                    parsed_data[k] = json.loads(v)
                except json.JSONDecodeError:
                    parsed_data[k] = v
                    
            return parsed_data
            
        except Exception as e:
            logger.error(f"Failed to get metrics for {service_name}: {e}")
            return None
    
    async def store_system_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Store overall system metrics."""
        try:
            key = "system:metrics"
            
            metrics_data = {
                "timestamp": datetime.utcnow().isoformat(),
                **metrics
            }
            
            await self.redis.hset(key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in metrics_data.items()
            })
            
            await self.redis.expire(key, settings.health_data_ttl_seconds)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store system metrics: {e}")
            return False
    
    async def get_system_metrics(self) -> Optional[Dict[str, Any]]:
        """Get overall system metrics."""
        try:
            key = "system:metrics"
            data = await self.redis.hgetall(key)
            
            if not data:
                return None
                
            # Parse JSON fields
            parsed_data = {}
            for k, v in data.items():
                try:
                    parsed_data[k] = json.loads(v)
                except json.JSONDecodeError:
                    parsed_data[k] = v
                    
            return parsed_data
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return None
    
    async def store_alert(self, alert: Dict[str, Any]) -> bool:
        """Store alert information."""
        try:
            alert_id = alert["id"]
            key = f"alert:{alert_id}"
            
            await self.redis.hset(key, mapping={
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in alert.items()
            })
            
            # Store in active alerts list if active
            if alert.get("status") == "active":
                await self.redis.sadd("alerts:active", alert_id)
            
            await self.redis.expire(key, settings.health_data_ttl_seconds)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")
            return False
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active alerts."""
        try:
            alert_ids = await self.redis.smembers("alerts:active")
            alerts = []
            
            for alert_id in alert_ids:
                key = f"alert:{alert_id}"
                data = await self.redis.hgetall(key)
                
                if data:
                    # Parse JSON fields
                    parsed_alert = {}
                    for k, v in data.items():
                        try:
                            parsed_alert[k] = json.loads(v)
                        except json.JSONDecodeError:
                            parsed_alert[k] = v
                    alerts.append(parsed_alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    async def resolve_alert(self, alert_id: str) -> bool:
        """Mark alert as resolved."""
        try:
            key = f"alert:{alert_id}"
            await self.redis.hset(key, "status", "resolved")
            await self.redis.hset(key, "resolved_at", datetime.utcnow().isoformat())
            
            # Remove from active alerts
            await self.redis.srem("alerts:active", alert_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            await self.redis.ping()
            return True
        except Exception:
            return False