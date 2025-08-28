"""
HTTP client for service-to-service communication in NeverMissCall.

Provides ServiceClient class following the authentication patterns
defined in authentication-standards.md.
"""

import httpx
import time
from typing import Any, Dict, Optional
from ..models.api import ApiResponse
from ..models.exceptions import ExternalServiceError, UnauthorizedError
from .logger import logger


class ServiceClient:
    """
    HTTP client for service-to-service communication.
    
    Handles authentication, request/response logging, and error handling
    following the patterns defined in authentication-standards.md.
    """
    
    def __init__(self, service_key: str, timeout: int = 30):
        """
        Initialize service client with authentication key.
        
        Args:
            service_key: Service-to-service authentication key
            timeout: Request timeout in seconds
        """
        self.service_key = service_key
        self.timeout = timeout
        
        # Create HTTP client with common headers
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                'X-Service-Key': service_key,
                'Content-Type': 'application/json',
                'User-Agent': 'NeverMissCall-ServiceClient/1.0'
            }
        )
    
    async def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """
        Perform GET request to another service.
        
        Args:
            url: Request URL
            params: Optional query parameters
            headers: Optional additional headers
            
        Returns:
            ApiResponse object
        """
        return await self._request('GET', url, params=params, headers=headers)
    
    async def post(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """
        Perform POST request to another service.
        
        Args:
            url: Request URL
            data: Optional request body data
            headers: Optional additional headers
            
        Returns:
            ApiResponse object
        """
        return await self._request('POST', url, json=data, headers=headers)
    
    async def put(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """
        Perform PUT request to another service.
        
        Args:
            url: Request URL
            data: Optional request body data
            headers: Optional additional headers
            
        Returns:
            ApiResponse object
        """
        return await self._request('PUT', url, json=data, headers=headers)
    
    async def patch(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """
        Perform PATCH request to another service.
        
        Args:
            url: Request URL
            data: Optional request body data
            headers: Optional additional headers
            
        Returns:
            ApiResponse object
        """
        return await self._request('PATCH', url, json=data, headers=headers)
    
    async def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> ApiResponse:
        """
        Perform DELETE request to another service.
        
        Args:
            url: Request URL
            headers: Optional additional headers
            
        Returns:
            ApiResponse object
        """
        return await self._request('DELETE', url, headers=headers)
    
    async def _request(self, method: str, url: str, **kwargs) -> ApiResponse:
        """
        Internal method to perform HTTP requests with error handling.
        
        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            ApiResponse object
            
        Raises:
            ExternalServiceError: On service communication failures
            UnauthorizedError: On authentication failures
        """
        start_time = time.time()
        
        try:
            # Merge additional headers with default headers
            request_headers = self._client.headers.copy()
            if 'headers' in kwargs:
                request_headers.update(kwargs.pop('headers'))
            
            # Log outgoing request
            logger.info(f"Service request: {method} {url}", extra={
                'event_type': 'service_request',
                'method': method,
                'url': url,
                'service_key_present': bool(self.service_key)
            })
            
            # Make HTTP request
            response = await self._client.request(
                method=method,
                url=url,
                headers=request_headers,
                **kwargs
            )
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log response
            logger.info(f"Service response: {method} {url} {response.status_code} ({duration_ms}ms)", extra={
                'event_type': 'service_response',
                'method': method,
                'url': url,
                'status_code': response.status_code,
                'duration_ms': duration_ms
            })
            
            # Handle authentication errors
            if response.status_code == 401:
                raise UnauthorizedError("Service authentication failed")
            
            # Handle other HTTP errors
            if response.status_code >= 400:
                error_text = await response.aread() if hasattr(response, 'aread') else response.text
                raise ExternalServiceError(
                    message=f"Service request failed: {response.status_code}",
                    service=self._extract_service_name(url),
                    status_code=response.status_code,
                    response=error_text
                )
            
            # Parse response
            try:
                response_data = response.json()
                
                # If response follows our ApiResponse format, return it directly
                if isinstance(response_data, dict) and 'success' in response_data:
                    return ApiResponse(**response_data)
                
                # Otherwise, wrap in successful ApiResponse
                return ApiResponse(success=True, data=response_data)
                
            except Exception as parse_error:
                logger.error(f"Failed to parse service response", error=parse_error, extra={
                    'url': url,
                    'status_code': response.status_code
                })
                
                # Return raw text response
                response_text = response.text if hasattr(response, 'text') else str(response.content)
                return ApiResponse(success=True, data={'raw_response': response_text})
        
        except httpx.TimeoutException as error:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Service request timeout: {method} {url} ({duration_ms}ms)", error=error)
            
            raise ExternalServiceError(
                message=f"Service request timed out after {self.timeout}s",
                service=self._extract_service_name(url),
                status_code=408,
                response=str(error)
            )
        
        except httpx.NetworkError as error:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Service network error: {method} {url} ({duration_ms}ms)", error=error)
            
            raise ExternalServiceError(
                message=f"Network error communicating with service",
                service=self._extract_service_name(url),
                status_code=0,
                response=str(error)
            )
        
        except Exception as error:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected service error: {method} {url} ({duration_ms}ms)", error=error)
            
            raise ExternalServiceError(
                message=f"Unexpected error: {str(error)}",
                service=self._extract_service_name(url),
                status_code=0,
                response=str(error)
            )
    
    def _extract_service_name(self, url: str) -> str:
        """
        Extract service name from URL for error reporting.
        
        Args:
            url: Request URL
            
        Returns:
            Service name
        """
        try:
            # Extract hostname or service identifier from URL
            if '://' in url:
                # Full URL - extract hostname
                host = url.split('://')[1].split('/')[0].split(':')[0]
                return host
            else:
                # Relative URL - return generic identifier
                return 'unknown-service'
        except:
            return 'unknown-service'
    
    async def health_check(self, service_url: str) -> Dict[str, Any]:
        """
        Perform health check on a service.
        
        Args:
            service_url: Base URL of the service
            
        Returns:
            Health check response data
        """
        try:
            health_url = f"{service_url.rstrip('/')}/health"
            response = await self.get(health_url)
            
            return {
                'healthy': response.success,
                'status': response.data if response.success else None,
                'error': response.error if not response.success else None
            }
        
        except Exception as error:
            logger.error(f"Health check failed for {service_url}", error=error)
            return {
                'healthy': False,
                'status': None,
                'error': str(error)
            }
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience function to create authenticated service client
def create_service_client(service_key: Optional[str] = None) -> ServiceClient:
    """
    Create service client with authentication key from environment.
    
    Args:
        service_key: Optional service key (uses env var if not provided)
        
    Returns:
        ServiceClient instance
    """
    import os
    
    if not service_key:
        service_key = os.getenv('INTERNAL_SERVICE_KEY', 'nmc-internal-services-auth-key-phase1')
    
    return ServiceClient(service_key)