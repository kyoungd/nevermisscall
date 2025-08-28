# Dispatch Bot AI API

AI-powered scheduling and response platform for field service professionals.

## Overview

The Dispatch Bot AI API provides intelligent conversation processing for field service businesses, enabling automated scheduling, emergency detection, and customer communication. Built with FastAPI and following test-driven development principles.

## Features

- **Health Check Endpoint**: Monitor API status and service health
- **Conversation Processing**: Process customer messages and extract intent, urgency, and scheduling information
- **Request Validation**: Comprehensive input validation with detailed error responses
- **Structured Logging**: JSON-formatted logging for production monitoring
- **Error Handling**: Graceful error handling with standardized error responses
- **Environment Configuration**: Flexible configuration through environment variables

## Project Structure

```
dispatch_bot/
├── src/dispatch_bot/           # Application source code
│   ├── api/                    # API-specific modules
│   │   ├── __init__.py
│   │   └── exceptions.py       # Exception handlers
│   ├── config/                 # Configuration modules
│   │   ├── __init__.py
│   │   ├── logging.py          # Logging configuration
│   │   └── settings.py         # Application settings
│   ├── models/                 # Data models
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   ├── utils/                  # Utility functions
│   │   └── __init__.py
│   ├── __init__.py
│   └── main.py                 # FastAPI application
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   │   ├── test_health.py      # Health endpoint tests
│   │   └── test_dispatch_endpoint.py # Dispatch endpoint tests
│   ├── integration/            # Integration tests
│   └── __init__.py
├── docs/                       # Documentation
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore file
└── README.md                   # This file
```

## Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

### Installation

1. **Clone the repository** (or navigate to the project directory):
   ```bash
   cd /home/young/Desktop/Code/nvermisscall/nmc-ai
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**:
   ```bash
   PYTHONPATH=src python -m dispatch_bot.main
   ```

   Or using uvicorn directly:
   ```bash
   PYTHONPATH=src uvicorn dispatch_bot.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - ReDoc Documentation: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

## API Endpoints

### Health Check

```http
GET /health
```

Returns API health status and service information.

**Example Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-08-07T10:30:00Z",
  "services": {
    "database": "healthy",
    "geocoding": "healthy",
    "llm": "healthy",
    "traffic": "healthy"
  },
  "uptime_seconds": 3600
}
```

### Process Conversation

```http
POST /dispatch/process
```

Process a customer conversation turn and determine next actions.

**Example Request:**
```json
{
  "caller_phone": "+12125551234",
  "called_number": "+15555551111",
  "current_message": "Water heater burst in basement! 789 Sunset Blvd, 90210",
  "business_name": "Prime Plumbing",
  "trade_type": "plumbing",
  "business_hours": {
    "monday": {"start": "07:00", "end": "18:00"}
  },
  "phone_hours": {
    "always_available": true
  },
  "business_address": {
    "street_address": "123 Main St",
    "city": "Los Angeles", 
    "state": "CA",
    "postal_code": "90210",
    "latitude": 34.0522,
    "longitude": -118.2437
  },
  "job_estimates": [...],
  "business_settings": {...}
}
```

**Example Response:**
```json
{
  "extracted_info": {
    "job_type": "water_heater_repair",
    "urgency_level": "emergency",
    "customer_address": "789 Sunset Blvd, 90210"
  },
  "validation": {
    "service_area_valid": true,
    "trade_supported": true
  },
  "next_action": {
    "action_type": "request_confirmation",
    "message_to_customer": "🚨 Emergency detected! I can get our tech to you today. Reply YES to confirm."
  },
  "conversation_stage": "confirming"
}
```

## Running Tests

The project uses pytest for testing with a test-driven development approach.

### Run All Tests

```bash
PYTHONPATH=src python -m pytest
```

### Run Tests with Coverage

```bash
PYTHONPATH=src python -m pytest --cov=dispatch_bot --cov-report=html
```

### Run Specific Test Files

```bash
# Health check tests
PYTHONPATH=src python -m pytest tests/unit/test_health.py -v

# Dispatch endpoint tests  
PYTHONPATH=src python -m pytest tests/unit/test_dispatch_endpoint.py -v
```

## Configuration

The application can be configured via environment variables:

### Environment Variables

```bash
# Application Settings
DISPATCH_BOT_ENVIRONMENT=development  # development, production, test
DISPATCH_BOT_HOST=0.0.0.0
DISPATCH_BOT_PORT=8000
DISPATCH_BOT_RELOAD=true

# Logging Settings
DISPATCH_BOT_LOGGING__LEVEL=INFO      # DEBUG, INFO, WARNING, ERROR
DISPATCH_BOT_LOGGING__JSON_LOGS=true

# API Settings  
DISPATCH_BOT_API__DEBUG=false
DISPATCH_BOT_API__DOCS_URL=/docs

# External Services (for production)
DISPATCH_BOT_EXTERNAL_SERVICES__GEOCODING_API_KEY=your_key
DISPATCH_BOT_EXTERNAL_SERVICES__LLM_API_KEY=your_key
```

### Configuration File

You can also create a `.env` file in the project root:

```bash
DISPATCH_BOT_ENVIRONMENT=development
DISPATCH_BOT_LOGGING__LEVEL=DEBUG
DISPATCH_BOT_API__DEBUG=true
```

## Development

### Code Style

The project uses several tools for code quality:

- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking

```bash
# Format code
black src/ tests/

# Lint code  
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:

```bash
pre-commit install
```

### Adding New Features

1. **Write Tests First**: Following TDD, write failing tests for new functionality
2. **Implement Code**: Write the minimum code to make tests pass
3. **Refactor**: Improve code quality while keeping tests passing
4. **Document**: Update documentation and type hints

## Production Deployment

### Using Gunicorn

```bash
PYTHONPATH=src gunicorn dispatch_bot.main:app -w 4 -k uvicorn.workers.UnicornWorker
```

### Environment Configuration for Production

```bash
DISPATCH_BOT_ENVIRONMENT=production
DISPATCH_BOT_LOGGING__JSON_LOGS=true
DISPATCH_BOT_API__DEBUG=false
DISPATCH_BOT_API__DOCS_URL=null  # Disable docs in production
```

## Architecture

### Design Principles

- **Test-Driven Development**: All features are developed test-first
- **SOLID Principles**: Clean, maintainable, and extensible code
- **Separation of Concerns**: Clear module boundaries and responsibilities
- **Configuration Management**: Environment-based configuration
- **Error Handling**: Comprehensive error handling with structured responses
- **Logging**: Structured logging for monitoring and debugging

### Key Components

- **FastAPI**: Modern, fast web framework with automatic API documentation
- **Pydantic**: Data validation and serialization with type hints
- **Structlog**: Structured logging for better observability
- **Pytest**: Testing framework with fixtures and parametrization

## API Specification

For detailed API specification including all request/response schemas, see the auto-generated documentation:
- OpenAPI/Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Implement the feature
5. Ensure all tests pass
6. Submit a pull request

## License

This project is private and proprietary.

## Support

For questions or issues, please contact the development team.