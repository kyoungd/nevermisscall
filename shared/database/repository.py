"""
Base repository pattern for database operations.

Provides BaseRepository class for common CRUD operations
following the patterns defined in shared.md documentation.
"""

import logging
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel

from .connection import get_database

logger = logging.getLogger(__name__)

# Type variable for generic repository
T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T]):
    """
    Simple base repository for common database operations.
    
    Follows the patterns defined in the shared library documentation
    for consistent data access across all microservices.
    """
    
    def __init__(self, table_name: str, model_class: type[T]):
        """
        Initialize repository with table name and model class.
        
        Args:
            table_name: Database table name
            model_class: Pydantic model class for type validation
        """
        self.table_name = table_name
        self.model_class = model_class
        self.db = get_database()
    
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create new record in database.
        
        Args:
            data: Dictionary of field values
            
        Returns:
            Created record as model instance
        """
        try:
            # Build INSERT query
            fields = list(data.keys())
            placeholders = [f'${i+1}' for i in range(len(fields))]
            values = list(data.values())
            
            sql = f"""
                INSERT INTO {self.table_name} ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                RETURNING *
            """
            
            result = await self.db.query(sql, values)
            if not result:
                raise RuntimeError("Create operation failed - no data returned")
                
            return self.model_class(**result[0])
            
        except Exception as error:
            logger.error(f"Create failed in {self.table_name}: {error}")
            raise
    
    async def find_by_id(self, id: str) -> Optional[T]:
        """
        Find record by ID.
        
        Args:
            id: Record ID (UUID string)
            
        Returns:
            Model instance or None if not found
        """
        try:
            sql = f"SELECT * FROM {self.table_name} WHERE id = $1"
            result = await self.db.query(sql, [id])
            
            if not result:
                return None
                
            return self.model_class(**result[0])
            
        except Exception as error:
            logger.error(f"Find by ID failed in {self.table_name}: {error}")
            raise
    
    async def find_by_filters(self, filters: Dict[str, Any]) -> List[T]:
        """
        Find records matching filter conditions.
        
        Args:
            filters: Dictionary of field/value pairs for WHERE conditions
            
        Returns:
            List of model instances
        """
        try:
            if not filters:
                sql = f"SELECT * FROM {self.table_name}"
                params = []
            else:
                # Build WHERE clause
                conditions = []
                params = []
                param_count = 1
                
                for field, value in filters.items():
                    conditions.append(f"{field} = ${param_count}")
                    params.append(value)
                    param_count += 1
                
                sql = f"SELECT * FROM {self.table_name} WHERE {' AND '.join(conditions)}"
            
            result = await self.db.query(sql, params)
            
            return [self.model_class(**record) for record in result]
            
        except Exception as error:
            logger.error(f"Find by filters failed in {self.table_name}: {error}")
            raise
    
    async def get_paginated(self, page: int, limit: int, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get paginated results.
        
        Args:
            page: Page number (1-based)
            limit: Records per page
            filters: Optional filter conditions
            
        Returns:
            Dictionary with data, total, page, and limit
        """
        try:
            offset = (page - 1) * limit
            
            # Build base query
            if filters:
                conditions = []
                params = []
                param_count = 1
                
                for field, value in filters.items():
                    conditions.append(f"{field} = ${param_count}")
                    params.append(value)
                    param_count += 1
                
                where_clause = f" WHERE {' AND '.join(conditions)}"
            else:
                where_clause = ""
                params = []
            
            # Get total count
            count_sql = f"SELECT COUNT(*) FROM {self.table_name}{where_clause}"
            count_result = await self.db.query(count_sql, params)
            total = count_result[0]['count']
            
            # Get paginated data
            data_sql = f"SELECT * FROM {self.table_name}{where_clause} LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
            data_params = params + [limit, offset]
            
            data_result = await self.db.query(data_sql, data_params)
            data = [self.model_class(**record) for record in data_result]
            
            return {
                'data': data,
                'total': total,
                'page': page,
                'limit': limit
            }
            
        except Exception as error:
            logger.error(f"Paginated query failed in {self.table_name}: {error}")
            raise
    
    async def update_status(self, id: str, status: str, additional_data: Optional[Dict[str, Any]] = None) -> Optional[T]:
        """
        Update record status with optional additional data.
        
        Args:
            id: Record ID
            status: New status value
            additional_data: Optional additional fields to update
            
        Returns:
            Updated model instance or None if not found
        """
        try:
            # Build UPDATE query
            updates = ['status = $2']
            params = [id, status]
            param_count = 3
            
            if additional_data:
                for field, value in additional_data.items():
                    updates.append(f"{field} = ${param_count}")
                    params.append(value)
                    param_count += 1
            
            # Add updated_at timestamp if column exists
            updates.append(f"updated_at = NOW()")
            
            sql = f"""
                UPDATE {self.table_name} 
                SET {', '.join(updates)}
                WHERE id = $1
                RETURNING *
            """
            
            result = await self.db.query(sql, params)
            
            if not result:
                return None
                
            return self.model_class(**result[0])
            
        except Exception as error:
            logger.error(f"Update status failed in {self.table_name}: {error}")
            raise
    
    async def get_statistics(self, tenant_id: Optional[str] = None) -> Dict[str, int]:
        """
        Get basic statistics for the table.
        
        Args:
            tenant_id: Optional tenant filter
            
        Returns:
            Dictionary with count statistics
        """
        try:
            # Base count query
            if tenant_id:
                sql = f"SELECT COUNT(*) as total FROM {self.table_name} WHERE tenant_id = $1"
                params = [tenant_id]
            else:
                sql = f"SELECT COUNT(*) as total FROM {self.table_name}"
                params = []
            
            result = await self.db.query(sql, params)
            total = result[0]['total']
            
            # Try to get status breakdown if status column exists
            stats = {'total': total}
            
            try:
                if tenant_id:
                    status_sql = f"""
                        SELECT status, COUNT(*) as count 
                        FROM {self.table_name} 
                        WHERE tenant_id = $1 
                        GROUP BY status
                    """
                    status_params = [tenant_id]
                else:
                    status_sql = f"""
                        SELECT status, COUNT(*) as count 
                        FROM {self.table_name} 
                        GROUP BY status
                    """
                    status_params = []
                
                status_result = await self.db.query(status_sql, status_params)
                
                for row in status_result:
                    stats[f"status_{row['status']}"] = row['count']
                    
            except Exception:
                # Status column might not exist, skip status breakdown
                pass
            
            return stats
            
        except Exception as error:
            logger.error(f"Get statistics failed in {self.table_name}: {error}")
            raise