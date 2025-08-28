"""
Phase 1 Settings - Simplified configuration for basic working system.
Loads from .env file using python-dotenv.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class GoogleMapsSettings(BaseModel):
    """Google Maps API configuration for Phase 1"""
    api_key: Optional[str] = Field(default=None, description="Google Maps API key")
    geocoding_url: str = Field(
        default="https://maps.googleapis.com/maps/api/geocode/json",
        description="Google Maps Geocoding API URL"
    )
    distance_matrix_url: str = Field(
        default="https://maps.googleapis.com/maps/api/distancematrix/json",
        description="Google Maps Distance Matrix API URL"
    )


class OpenAISettings(BaseModel):
    """OpenAI API configuration for Phase 1"""
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    temperature: float = Field(default=0.1, description="Model temperature")
    max_tokens: int = Field(default=500, description="Maximum tokens in response")


class BusinessSettings(BaseModel):
    """Default business configuration for Phase 1"""
    default_hours_start: str = Field(default="07:00", description="Default business start time")
    default_hours_end: str = Field(default="18:00", description="Default business end time")
    default_service_radius_miles: int = Field(default=25, description="Default service radius")
    default_trade_type: str = Field(default="plumbing", description="Default trade type")
    
    # Phase 1 job estimates
    default_job_estimate_min: float = Field(default=100.0, description="Default minimum job estimate")
    default_job_estimate_max: float = Field(default=300.0, description="Default maximum job estimate")


class Phase1Settings(BaseSettings):
    """
    Phase 1 application settings - simplified for basic working system.
    
    Loads configuration from .env file without prefixes for simplicity.
    """
    
    # Application info
    app_name: str = Field(default="Never Missed Call AI", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=True, description="Debug mode")
    log_level: str = Field(default="debug", description="Logging level")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # API Keys from environment
    google_maps_api_key: Optional[str] = Field(default=None, description="Google Maps API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    
    # Service configurations
    google_maps: GoogleMapsSettings = Field(default_factory=GoogleMapsSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    business: BusinessSettings = Field(default_factory=BusinessSettings)
    
    # Rate limiting
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    rate_limit_per_hour: int = Field(default=1000, description="Rate limit per hour")
    
    # Security
    secret_key: str = Field(default="dev_secret_key_change_in_production", description="Secret key")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", description="Allowed hosts")
    
    # Logging
    log_file: str = Field(default="logs/nmc-ai.log", description="Log file path")
    log_max_size_mb: int = Field(default=10, description="Max log file size in MB")
    log_backup_count: int = Field(default=5, description="Number of log backups")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8", 
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # After initialization, update nested settings with environment values
        if self.google_maps_api_key:
            self.google_maps.api_key = self.google_maps_api_key
        if self.openai_api_key:
            self.openai.api_key = self.openai_api_key
    
    @property
    def is_debug(self) -> bool:
        """Check if running in debug mode"""
        return self.debug
    
    @property
    def has_google_maps_key(self) -> bool:
        """Check if Google Maps API key is configured"""
        return self.google_maps.api_key is not None and len(self.google_maps.api_key) > 0
    
    @property
    def has_openai_key(self) -> bool:
        """Check if OpenAI API key is configured"""
        return self.openai.api_key is not None and len(self.openai.api_key) > 0
    
    def validate_required_keys(self) -> dict:
        """
        Validate that required API keys are present.
        Returns dict with validation results.
        """
        validation = {
            "valid": True,
            "missing_keys": [],
            "warnings": []
        }
        
        if not self.has_google_maps_key:
            validation["missing_keys"].append("GOOGLE_MAPS_API_KEY")
            validation["valid"] = False
        
        if not self.has_openai_key:
            validation["missing_keys"].append("OPENAI_API_KEY") 
            validation["valid"] = False
        
        if not validation["valid"]:
            validation["warnings"].append(
                f"Missing required API keys: {', '.join(validation['missing_keys'])}"
            )
            validation["warnings"].append(
                "Add these keys to your .env file before running the application"
            )
        
        return validation


# Global settings instance for Phase 1
phase1_settings = Phase1Settings()


def get_phase1_settings() -> Phase1Settings:
    """
    Get the Phase 1 settings instance.
    
    This function can be overridden in tests to provide test-specific settings.
    """
    return phase1_settings


def validate_environment() -> dict:
    """
    Validate that the environment is properly configured for Phase 1.
    
    Returns:
        Dict with validation results
    """
    settings = get_phase1_settings()
    validation = settings.validate_required_keys()
    
    # Add environment info
    validation["environment"] = {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "log_level": settings.log_level
    }
    
    return validation