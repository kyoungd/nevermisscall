# dispatch-bot-ai Operations Runbook

## Service Overview
The Dispatch Bot AI service provides intelligent call handling, natural language processing, appointment scheduling, and automated dispatch for service calls using OpenAI and custom ML models.

## Environments

| Environment | URL | Database | Port | Purpose |
|------------|-----|----------|------|---------|  
| Development | http://localhost:8000 | postgresql://localhost:5432/nevermisscall | 8000 | Local development |
| Staging | https://staging-api.nevermisscall.com/ai | postgresql://staging-db:5432/nevermisscall | 8000 | Pre-production |
| Production | https://api.nevermisscall.com/ai | postgresql://prod-db:5432/nevermisscall | 8000 | Live environment |

### Environment Variables
```bash
PYTHON_ENV=production
PORT=8000
DATABASE_URL=postgresql://nevermisscall:password@localhost:5432/nevermisscall
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_MAPS_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MODEL_NAME=gpt-4-turbo-preview
MAX_TOKENS=2000
TEMPERATURE=0.7
ENABLE_FALLBACK=true
LOG_LEVEL=info
```

## Deployment

### Deploy Steps
```bash
# 1. Pull and setup
cd /home/nevermisscall/nmc-main/dispatch-bot-ai
git pull origin main

# 2. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head

# 4. Validate API keys
python scripts/validate_apis.py

# 5. Reload service
pm2 reload dispatch-bot-ai

# 6. Test conversation flow
python scripts/test_conversation.py
```

## Monitoring & Alerts

### Key Metrics
| Metric | Threshold | Alert Level | Action |
|--------|-----------|-------------|--------|
| API Response Time | > 3s | WARNING | Check OpenAI status |
| Token Usage | > 90% quota | WARNING | Increase limits |
| Fallback Rate | > 10% | WARNING | Check primary model |
| Error Rate | > 5% | CRITICAL | Check logs |
| Cost per Call | > $0.50 | INFO | Optimize prompts |

## Common Incidents & Fixes

### 1. OpenAI API Rate Limiting
```bash
# Check current usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Enable fallback mode
export ENABLE_FALLBACK=true
export FALLBACK_MODEL=gpt-3.5-turbo
pm2 restart dispatch-bot-ai --update-env

# Implement request queuing
export ENABLE_QUEUE=true
export MAX_CONCURRENT_REQUESTS=5
pm2 restart dispatch-bot-ai --update-env
```

### 2. Conversation Context Loss
```bash
# Check Redis for context
redis-cli GET "conversation:conv-123"

# Rebuild context from database
python scripts/rebuild_context.py --conversation-id conv-123

# Increase context window
export MAX_CONTEXT_MESSAGES=20
pm2 restart dispatch-bot-ai --update-env
```

### 3. Geocoding Failures
```bash
# Test Google Maps API
curl "https://maps.googleapis.com/maps/api/geocode/json?address=123+Main+St&key=$GOOGLE_MAPS_API_KEY"

# Enable address caching
export ENABLE_GEOCODE_CACHE=true
export CACHE_TTL=86400
pm2 restart dispatch-bot-ai --update-env

# Use fallback geocoding
export FALLBACK_GEOCODER=nominatim
pm2 restart dispatch-bot-ai --update-env
```

## Performance Tuning

```bash
# Optimize model parameters
export TEMPERATURE=0.5  # More deterministic
export MAX_TOKENS=1500  # Reduce token usage
export TOP_P=0.9

# Enable response caching
export ENABLE_RESPONSE_CACHE=true
export CACHE_SIMILAR_THRESHOLD=0.85

# Use streaming responses
export ENABLE_STREAMING=true

pm2 restart dispatch-bot-ai --update-env
```

## Cost Management

```bash
# Monitor daily usage
python scripts/usage_report.py --date today

# Set spending limits
export DAILY_SPEND_LIMIT=100
export HOURLY_SPEND_LIMIT=10

# Optimize prompts
python scripts/optimize_prompts.py --analyze-last-days 7
```

## Backup & Restore

```bash
# Backup conversation data
pg_dump -h localhost -U nevermisscall -d nevermisscall \
  -t conversations -t conversation_messages -t ai_responses \
  -Fc -f /backup/db/ai-$(date +%Y%m%d).dump

# Export model fine-tuning data
python scripts/export_training_data.py \
  --output /backup/training/data-$(date +%Y%m%d).jsonl
```

## Disaster Recovery

- **RPO**: 15 minutes
- **RTO**: 5 minutes

### Fallback Procedures
```bash
# 1. Switch to rule-based fallback
export AI_MODE=rules_based
python scripts/activate_fallback.py

# 2. Use cached responses
export USE_CACHED_ONLY=true
pm2 restart dispatch-bot-ai --update-env

# 3. Route to human operators
export ROUTE_TO_HUMAN=true
export HUMAN_THRESHOLD=0.7
pm2 restart dispatch-bot-ai --update-env
```

## Contact Information

- **Service Owner**: AI Team
- **Oncall**: ai-oncall@nevermisscall.com
- **Slack**: #dispatch-ai-alerts
- **OpenAI Support**: support@openai.com