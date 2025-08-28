"""
Unit tests for configuration management.

Tests configuration loading, environment variable handling, and service
URL generation following unittest patterns and real configuration scenarios.
"""

import unittest
from unittest.mock import patch, MagicMock
import os

from shared.config import (
    get_common_config,
    get_service_config,
    get_service_url,
    SERVICE_PORTS,
    validate_required_env_vars,
    get_environment_info
)
from shared.config.settings import (
    CommonConfig,
    DatabaseConfigSection,
    JwtConfigSection,
    ServiceAuthConfigSection
)


class TestConfigurationLoading(unittest.TestCase):
    """Test configuration loading handles real deployment scenarios."""
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://test:test@localhost:5432/testdb',
        'JWT_SECRET': 'test-jwt-secret-key',
        'INTERNAL_SERVICE_KEY': 'test-service-key',
        'PYTHON_ENV': 'testing',
        'LOG_LEVEL': 'debug',
        'DB_MAX_CONNECTIONS': '10'
    })
    def test_get_common_config_loads_from_environment(self):
        """Test get_common_config loads configuration from environment variables."""
        config = get_common_config()
        
        self.assertIsInstance(config, CommonConfig)
        self.assertEqual(config.python_env, 'testing')
        self.assertEqual(config.log_level, 'debug')
        
        # Database config
        self.assertEqual(config.database.url, 'postgresql://test:test@localhost:5432/testdb')
        self.assertEqual(config.database.max_connections, 10)
        
        # JWT config
        self.assertEqual(config.jwt.secret, 'test-jwt-secret-key')
        self.assertEqual(config.jwt.expires_in, '24h')  # Default value
        
        # Service auth config
        self.assertEqual(config.service_auth.key, 'test-service-key')
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_common_config_uses_sensible_defaults(self):
        """Test get_common_config uses sensible defaults for production deployment."""
        config = get_common_config()
        
        # Should use defaults when env vars not set
        self.assertEqual(config.python_env, 'development')
        self.assertEqual(config.log_level, 'debug')
        
        # Database defaults
        expected_db_url = 'postgresql://nevermisscall_user:nevermisscall_admin411@localhost:5432/nevermisscall'
        self.assertEqual(config.database.url, expected_db_url)
        self.assertEqual(config.database.max_connections, 5)
        
        # Service auth default (from documentation)
        self.assertEqual(config.service_auth.key, 'nmc-internal-services-auth-key-phase1')
    
    def test_database_config_section_validates_structure(self):
        """Test DatabaseConfigSection validates database configuration structure."""
        db_config = DatabaseConfigSection(
            url='postgresql://localhost:5432/test',
            max_connections=5
        )
        
        self.assertEqual(db_config.url, 'postgresql://localhost:5432/test')
        self.assertEqual(db_config.max_connections, 5)
        
        # Test validation
        with self.assertRaises(ValueError):
            DatabaseConfigSection(
                url='postgresql://localhost:5432/test',
                max_connections='invalid'  # Should be integer
            )
    
    def test_jwt_config_section_validates_structure(self):
        """Test JwtConfigSection validates JWT configuration structure."""
        jwt_config = JwtConfigSection(
            secret='test-secret-key',
            expires_in='24h'
        )
        
        self.assertEqual(jwt_config.secret, 'test-secret-key')
        self.assertEqual(jwt_config.expires_in, '24h')


class TestServiceConfiguration(unittest.TestCase):
    """Test service-specific configuration handling."""
    
    def test_get_service_config_merges_common_and_specific(self):
        """Test get_service_config merges common config with service-specific settings."""
        service_specific = {
            'service_timeout': 30,
            'max_retries': 3
        }
        
        with patch('shared.config.get_common_config') as mock_common:
            mock_config = MagicMock()
            mock_config.dict.return_value = {
                'python_env': 'development',
                'database': {'url': 'postgresql://test'},
                'jwt': {'secret': 'secret'}
            }
            mock_common.return_value = mock_config
            
            merged_config = get_service_config('auth-service', service_specific)
            
            # Should include common config
            self.assertEqual(merged_config['python_env'], 'development')
            
            # Should include service-specific fields
            self.assertEqual(merged_config['service_name'], 'auth-service')
            self.assertEqual(merged_config['service_port'], 3301)  # From SERVICE_PORTS
            self.assertEqual(merged_config['service_timeout'], 30)
            self.assertEqual(merged_config['max_retries'], 3)
    
    def test_service_ports_mapping_covers_all_services(self):
        """Test SERVICE_PORTS mapping covers all documented services."""
        # These services are defined in the documentation
        expected_services = [
            'auth-service',
            'tenant-service', 
            'user-service',
            'config-service',
            'call-service',
            'alerts-service',
            'analytics-service',
            'provisioning-service',
            'connection-service',
            'infrastructure-service',
            'twilio-service',
            'ai-service',
            'calendar-service',
            'web-ui'
        ]
        
        for service in expected_services:
            with self.subTest(service=service):
                self.assertIn(service, SERVICE_PORTS, f"SERVICE_PORTS missing {service}")
                self.assertIsInstance(SERVICE_PORTS[service], int, f"{service} port should be integer")
                self.assertGreater(SERVICE_PORTS[service], 1000, f"{service} port should be > 1000")
    
    def test_get_service_url_generates_correct_urls(self):
        """Test get_service_url generates correct service URLs for communication."""
        # Test with default localhost
        auth_url = get_service_url('auth-service')
        self.assertEqual(auth_url, 'http://localhost:3301')
        
        # Test with custom host
        analytics_url = get_service_url('analytics-service', 'production-host')
        self.assertEqual(analytics_url, 'http://production-host:3102')
        
        # Test web-ui URL generation
        ui_url = get_service_url('web-ui')
        self.assertEqual(ui_url, 'http://localhost:3000')
    
    def test_get_service_url_raises_for_unknown_service(self):
        """Test get_service_url raises ValueError for unknown service names."""
        with self.assertRaises(ValueError) as context:
            get_service_url('nonexistent-service')
        
        error = context.exception
        self.assertIn("Unknown service: nonexistent-service", str(error))


class TestEnvironmentValidation(unittest.TestCase):
    """Test environment variable validation for deployment safety."""
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://test',
        'JWT_SECRET': 'test-secret',
        'INTERNAL_SERVICE_KEY': 'test-key'
    })
    def test_validate_required_env_vars_passes_with_all_vars(self):
        """Test validate_required_env_vars passes when all required vars are set."""
        missing = validate_required_env_vars()
        self.assertEqual(missing, {})
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_required_env_vars_identifies_missing_vars(self):
        """Test validate_required_env_vars identifies missing critical variables."""
        missing = validate_required_env_vars()
        
        # Should identify all required variables
        expected_missing = {
            'DATABASE_URL': 'PostgreSQL connection string',
            'JWT_SECRET': 'JWT signing secret key',
            'INTERNAL_SERVICE_KEY': 'Service-to-service authentication key'
        }
        
        self.assertEqual(missing, expected_missing)
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgresql://test',
        'JWT_SECRET': 'test-secret',
        'INTERNAL_SERVICE_KEY': 'test-key',
        'PYTHON_ENV': 'production'
    })
    def test_get_environment_info_provides_deployment_status(self):
        """Test get_environment_info provides useful deployment status information."""
        env_info = get_environment_info()
        
        # Should include environment details
        self.assertEqual(env_info['python_env'], 'production')
        self.assertTrue(env_info['database_configured'])
        self.assertTrue(env_info['jwt_configured'])
        self.assertTrue(env_info['service_auth_configured'])
        
        # Should include available services
        self.assertIsInstance(env_info['available_services'], list)
        self.assertIn('auth-service', env_info['available_services'])
        
        # Should show no missing vars
        self.assertEqual(env_info['missing_env_vars'], {})
    
    @patch.dict(os.environ, {}, clear=True)
    def test_get_environment_info_shows_configuration_problems(self):
        """Test get_environment_info identifies configuration problems for debugging."""
        env_info = get_environment_info()
        
        # Should show missing configuration
        self.assertGreater(len(env_info['missing_env_vars']), 0)
        self.assertIn('DATABASE_URL', env_info['missing_env_vars'])
        self.assertIn('JWT_SECRET', env_info['missing_env_vars'])


class TestConfigurationBusinessRules(unittest.TestCase):
    """Test configuration enforces real business rules and constraints."""
    
    def test_service_ports_follow_documentation_ranges(self):
        """Test service ports follow the documented port allocation ranges."""
        # From CLAUDE.md documentation:
        # - Identity & Onboarding Services: 330x range
        # - Analytics Services: 310x range  
        # - Infrastructure Services: 310x range
        # - Phone & Communication Services: 350x range
        # - External Integration Services: 370x+ range
        
        # Identity services should be in 330x range
        identity_services = ['auth-service', 'tenant-service', 'user-service', 'config-service']
        for service in identity_services:
            with self.subTest(service=service):
                port = SERVICE_PORTS[service]
                self.assertTrue(3301 <= port <= 3399, f"{service} port {port} not in 330x range")
        
        # Analytics services should be in 310x range
        analytics_services = ['alerts-service', 'analytics-service', 'connection-service', 'infrastructure-service']
        for service in analytics_services:
            with self.subTest(service=service):
                port = SERVICE_PORTS[service]
                self.assertTrue(3101 <= port <= 3199, f"{service} port {port} not in 310x range")
        
        # External services should be in 370x+ range
        external_services = ['twilio-service', 'ai-service', 'calendar-service']
        for service in external_services:
            with self.subTest(service=service):
                port = SERVICE_PORTS[service]
                self.assertTrue(port >= 3701, f"{service} port {port} not >= 3701")
    
    def test_default_service_auth_key_matches_documentation(self):
        """Test default service auth key matches authentication-standards.md."""
        config = get_common_config()
        
        # Should match the key specified in authentication-standards.md
        expected_key = 'nmc-internal-services-auth-key-phase1'
        self.assertEqual(config.service_auth.key, expected_key)
    
    def test_default_database_url_follows_single_database_architecture(self):
        """Test default database URL follows single database architecture."""
        config = get_common_config()
        
        # Should use the single database specified in database-architecture.md
        self.assertIn('nevermisscall', config.database.url)
        self.assertIn('nevermisscall_user', config.database.url)
        self.assertIn('localhost:5432', config.database.url)


if __name__ == '__main__':
    unittest.main()