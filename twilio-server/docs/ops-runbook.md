# twilio-server Operations Runbook

## Service Overview
The Twilio Server handles all telephony operations for NeverMissCall, including inbound/outbound calls, SMS messaging, call recording, transcription, and webhook processing. It serves as the bridge between Twilio's communication platform and our application services.

## Environments

| Environment | URL | Database | Port | Purpose |
|------------|-----|----------|------|---------|
| Development | http://localhost:3701 | postgresql://localhost:5432/nevermisscall | 3701 | Local development |
| Staging | https://staging-api.nevermisscall.com/twilio | postgresql://staging-db:5432/nevermisscall | 3701 | Pre-production testing |
| Production | https://api.nevermisscall.com/twilio | postgresql://prod-db:5432/nevermisscall | 3701 | Live environment |

### Environment Variables
```bash
NODE_ENV=production
PORT=3701
DATABASE_URL=postgresql://nevermisscall:password@localhost:5432/nevermisscall
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+14155551234
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WEBHOOK_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AS_CALL_SERVICE_URL=http://localhost:3304
DISPATCH_BOT_AI_URL=http://localhost:8000
INTERNAL_SERVICE_KEY=nmc-internal-services-auth-key-phase1
REDIS_URL=redis://localhost:6379
CALL_RECORDING_ENABLED=true
TRANSCRIPTION_ENABLED=true
MAX_CALL_DURATION=3600
SMS_RATE_LIMIT=100
LOG_LEVEL=info
```

## Deployment

### Deploy Steps
```bash
# 1. Pull latest code
cd /home/nevermisscall/nmc-main
git pull origin main

# 2. Install dependencies
cd twilio-server
npm install --production

# 3. Validate Twilio credentials
node scripts/validate-twilio-config.js

# 4. Update Twilio webhook URLs
node scripts/update-webhook-urls.js --env production

# 5. Clear call cache
redis-cli --scan --pattern "call:*" | xargs redis-cli DEL

# 6. Reload service with PM2
pm2 reload twilio-server

# 7. Verify deployment
curl -f http://localhost:3701/health || exit 1
curl -X POST http://localhost:3701/test/webhook-validation

# 8. Test call flow
node scripts/test-call-flow.js --number +14155552000
```

### Rollback Steps
```bash
# 1. Pause incoming calls
node scripts/pause-incoming-calls.js --reason "Emergency rollback"

# 2. Get previous commit
PREVIOUS_COMMIT=$(git rev-parse HEAD~1)
git checkout $PREVIOUS_COMMIT

# 3. Rebuild
cd twilio-server
npm install --production

# 4. Restore webhook URLs
node scripts/update-webhook-urls.js --env production --version previous

# 5. Clear cache
redis-cli FLUSHDB

# 6. Restart service
pm2 restart twilio-server

# 7. Resume incoming calls
node scripts/resume-incoming-calls.js

# 8. Alert team
echo "ROLLBACK: twilio-server reverted to $PREVIOUS_COMMIT" | mail -s "Critical Rollback" ops@nevermisscall.com
```

## Feature Flags

### Current Feature Flags
```javascript
{
  "features": {
    "call_recording": true,
    "voicemail_transcription": true,
    "sms_automation": true,
    "call_analytics": true,
    "ai_dispatch": true,
    "conference_calling": false,
    "international_calling": false,
    "mms_support": false
  }
}
```

### Toggle Feature Flag
```bash
# Disable call recording temporarily
curl -X PATCH http://localhost:3701/internal/features \
  -H "X-Internal-Key: $INTERNAL_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"feature": "call_recording", "enabled": false}'

# Enable conference calling
curl -X PATCH http://localhost:3701/internal/features \
  -H "X-Internal-Key: $INTERNAL_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"feature": "conference_calling", "enabled": true}'
```

## Monitoring & Alerts

### Key Metrics
| Metric | Threshold | Alert Level | Action |
|--------|-----------|-------------|---------|
| Call Success Rate | < 98% | CRITICAL | Check Twilio status and network |
| Webhook Processing Time | > 2s | WARNING | Optimize webhook handlers |
| Failed Call Attempts | > 10/min | CRITICAL | Check configuration and credits |
| SMS Delivery Rate | < 95% | WARNING | Check carrier issues |
| Transcription Queue | > 100 | WARNING | Scale transcription workers |
| Twilio Balance | < $100 | CRITICAL | Add funds immediately |
| Memory Usage | > 400MB | WARNING | Check for memory leaks |

### Monitoring Dashboards
- **Grafana**: https://monitoring.nevermisscall.com/d/twilio-server
- **Twilio Console**: https://console.twilio.com/dashboard
- **Call Analytics**: https://monitoring.nevermisscall.com/d/call-analytics
- **PM2 Monitor**: `pm2 monit` (select twilio-server)

### Health Check Endpoints
```bash
# Basic health
curl http://localhost:3701/health

# Twilio connection status
curl http://localhost:3701/health/twilio \
  -H "X-Internal-Key: $INTERNAL_SERVICE_KEY"

# Webhook validation
curl -X POST http://localhost:3701/webhooks/test \
  -H "X-Twilio-Signature: test-signature"
```

## Common Incidents & Fixes

### 1. Webhook Authentication Failures
**Symptoms**: Twilio webhooks being rejected
```bash
# Verify webhook signature
curl -X POST http://localhost:3701/debug/validate-signature \
  -H "X-Internal-Key: $INTERNAL_SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d @webhook-payload.json

# Update webhook auth token
export TWILIO_WEBHOOK_AUTH_TOKEN=$(node scripts/get-webhook-token.js)
pm2 restart twilio-server --update-env

# Whitelist Twilio IPs if needed
for ip in 54.172.60.0/23 54.244.51.0/24 54.171.127.192/27; do
  sudo iptables -A INPUT -s $ip -j ACCEPT
done

# Test webhook endpoint
twilio api:core:incoming-phone-numbers:list \
  --properties sid,phoneNumber,voiceUrl,smsUrl
```

### 2. Call Quality Issues
**Symptoms**: Poor audio quality or dropped calls
```bash
# Check call statistics
psql -d nevermisscall -c "
  SELECT 
    DATE_TRUNC('hour', created_at) as hour,
    AVG(duration) as avg_duration,
    COUNT(*) FILTER (WHERE status = 'completed') as completed,
    COUNT(*) FILTER (WHERE status = 'failed') as failed
  FROM calls
  WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY hour
  ORDER BY hour DESC;"

# Analyze call drops
node scripts/analyze-call-quality.js --last-hours 6

# Switch to backup Twilio number if needed
export TWILIO_PHONE_NUMBER=+14155559999
pm2 restart twilio-server --update-env

# Enable debug logging
export LOG_LEVEL=debug
pm2 restart twilio-server --update-env
```

### 3. SMS Delivery Failures
**Symptoms**: SMS messages not being delivered
```bash
# Check SMS queue
redis-cli LLEN "sms:queue"

# Review failed messages
psql -d nevermisscall -c "
  SELECT 
    to_number,
    message_body,
    error_code,
    error_message,
    created_at
  FROM sms_messages
  WHERE status = 'failed'
    AND created_at > NOW() - INTERVAL '1 hour'
  ORDER BY created_at DESC;"

# Retry failed messages
node scripts/retry-failed-sms.js --batch-size 10 --delay 1000

# Check 10DLC registration status
twilio api:messaging:v1:services:list
```

### 4. Recording Storage Issues
**Symptoms**: Call recordings not available
```bash
# Check storage usage
df -h /var/recordings

# Clean old recordings
find /var/recordings -name "*.mp3" -mtime +30 -delete

# Migrate to S3 if local storage full
node scripts/migrate-recordings-to-s3.js --older-than 7

# Verify recording URLs
psql -d nevermisscall -c "
  SELECT 
    call_sid,
    recording_url,
    recording_duration,
    created_at
  FROM call_recordings
  WHERE created_at > NOW() - INTERVAL '1 hour'
    AND recording_url IS NOT NULL;"
```

## Secrets Rotation

### Twilio Credentials Rotation
```bash
# 1. Generate new API key in Twilio Console
NEW_API_KEY="SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
NEW_API_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 2. Test new credentials
node scripts/test-twilio-auth.js \
  --api-key $NEW_API_KEY \
  --api-secret $NEW_API_SECRET

# 3. Update service with dual auth
export TWILIO_API_KEY=$NEW_API_KEY
export TWILIO_API_SECRET=$NEW_API_SECRET
export TWILIO_API_KEY_OLD=$OLD_API_KEY
export TWILIO_API_SECRET_OLD=$OLD_API_SECRET
pm2 reload twilio-server --update-env

# 4. Monitor for issues
tail -f /home/nevermisscall/.pm2/logs/twilio-server-error.log

# 5. Remove old credentials after 24 hours
unset TWILIO_API_KEY_OLD TWILIO_API_SECRET_OLD
pm2 reload twilio-server --update-env

# 6. Delete old API key in Twilio Console
twilio api:core:keys:remove --sid $OLD_API_KEY_SID
```

### Webhook Token Rotation
```bash
# 1. Generate new webhook token
NEW_WEBHOOK_TOKEN=$(openssl rand -base64 32)

# 2. Update Twilio webhook URLs with new token
node scripts/update-webhook-urls.js \
  --token $NEW_WEBHOOK_TOKEN \
  --rollout gradual

# 3. Update service to accept both tokens
export TWILIO_WEBHOOK_AUTH_TOKEN=$NEW_WEBHOOK_TOKEN
export TWILIO_WEBHOOK_AUTH_TOKEN_OLD=$OLD_TOKEN
pm2 reload twilio-server --update-env

# 4. Complete migration after 1 hour
unset TWILIO_WEBHOOK_AUTH_TOKEN_OLD
pm2 reload twilio-server --update-env
```

## Backup & Restore

### Backup Procedures
```bash
# 1. Backup call data
pg_dump -h localhost -U nevermisscall -d nevermisscall \
  -t calls -t call_recordings -t sms_messages -t call_transcriptions \
  -Fc -f /backup/db/twilio-$(date +%Y%m%d).dump

# 2. Backup recordings
rsync -av /var/recordings/ /backup/recordings/$(date +%Y%m%d)/

# 3. Export call logs
psql -d nevermisscall -c "\COPY (
  SELECT * FROM calls 
  WHERE created_at > NOW() - INTERVAL '30 days'
) TO '/backup/export/calls-$(date +%Y%m%d).csv' CSV HEADER;"

# 4. Backup Twilio configuration
twilio api:core:incoming-phone-numbers:list --properties sid,phoneNumber,voiceUrl,smsUrl \
  > /backup/config/twilio-numbers-$(date +%Y%m%d).json

# 5. Create backup manifest
echo "{
  \"timestamp\": \"$(date -Iseconds)\",
  \"call_count\": $(psql -t -c 'SELECT COUNT(*) FROM calls WHERE created_at > NOW() - INTERVAL \"30 days\";'),
  \"recording_count\": $(find /var/recordings -name '*.mp3' | wc -l),
  \"total_size\": \"$(du -sh /backup/$(date +%Y%m%d))\"
}" > /backup/manifest-twilio-$(date +%Y%m%d).json
```

### Restore Procedures
```bash
# 1. Stop service
pm2 stop twilio-server

# 2. Restore database
pg_restore -h localhost -U nevermisscall -d nevermisscall \
  -c -t calls -t call_recordings -t sms_messages \
  /backup/db/twilio-20240115.dump

# 3. Restore recordings
rsync -av /backup/recordings/20240115/ /var/recordings/

# 4. Restore Twilio configuration
node scripts/restore-twilio-config.js \
  --config /backup/config/twilio-numbers-20240115.json

# 5. Clear cache
redis-cli FLUSHDB

# 6. Start service
pm2 start twilio-server

# 7. Verify restoration
curl http://localhost:3701/health
node scripts/verify-call-flow.js
```

## Disaster Recovery

### Recovery Point Objective (RPO): 15 minutes
- Call data: Real-time database replication
- Recordings: Backed up every 15 minutes to S3
- SMS logs: Database with point-in-time recovery

### Recovery Time Objective (RTO): 5 minutes
- Service restart: 1 minute
- Twilio number failover: 2 minutes
- Database connection: 1 minute
- Verification: 1 minute

### DR Procedures
```bash
# 1. Activate DR mode
export DISASTER_RECOVERY_MODE=true
export TWILIO_PHONE_NUMBER=$DR_PHONE_NUMBER
pm2 restart twilio-server --update-env

# 2. Update Twilio routing
twilio phone-numbers:update $MAIN_PHONE_NUMBER \
  --voice-url https://dr.nevermisscall.com/webhooks/voice \
  --sms-url https://dr.nevermisscall.com/webhooks/sms

# 3. Verify call routing
twilio api:core:calls:create \
  --from $TWILIO_PHONE_NUMBER \
  --to +14155552000 \
  --url https://dr.nevermisscall.com/test/twiml

# 4. Monitor recovery
watch -n 5 "curl -s http://localhost:3701/health | jq ."

# 5. Return to normal operations
unset DISASTER_RECOVERY_MODE
export TWILIO_PHONE_NUMBER=$MAIN_PHONE_NUMBER
pm2 restart twilio-server --update-env

# 6. Update routing back to primary
twilio phone-numbers:update $MAIN_PHONE_NUMBER \
  --voice-url https://api.nevermisscall.com/webhooks/voice \
  --sms-url https://api.nevermisscall.com/webhooks/sms
```

## Performance Tuning

### Call Processing Optimization
```bash
# Enable connection pooling
export TWILIO_CONNECTION_POOL_SIZE=10
pm2 restart twilio-server --update-env

# Optimize webhook processing
export WEBHOOK_WORKER_THREADS=4
export WEBHOOK_QUEUE_SIZE=1000
pm2 restart twilio-server --update-env

# Enable response caching
redis-cli CONFIG SET maxmemory 2gb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Database Optimization
```sql
-- Add indexes for call queries
CREATE INDEX CONCURRENTLY idx_calls_tenant_created ON calls(tenant_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_calls_status ON calls(status) WHERE status IN ('in-progress', 'ringing');
CREATE INDEX CONCURRENTLY idx_sms_to_status ON sms_messages(to_number, status);

-- Partition large tables
CREATE TABLE calls_2024_q1 PARTITION OF calls
  FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

-- Update statistics
ANALYZE calls;
ANALYZE sms_messages;
ANALYZE call_recordings;
```

## Security Procedures

### Webhook Security Audit
```bash
# 1. Verify webhook signatures
tail -f /home/nevermisscall/.pm2/logs/twilio-server-out.log | \
  grep "Webhook signature" | \
  awk '{print $NF}' | \
  sort | uniq -c

# 2. Check for replay attacks
psql -d nevermisscall -c "
  SELECT 
    webhook_id,
    COUNT(*) as duplicate_count
  FROM webhook_logs
  WHERE created_at > NOW() - INTERVAL '1 hour'
  GROUP BY webhook_id
  HAVING COUNT(*) > 1;"

# 3. Audit webhook access
psql -d nevermisscall -c "
  SELECT 
    source_ip,
    COUNT(*) as request_count,
    COUNT(DISTINCT webhook_type) as endpoint_count
  FROM webhook_logs
  WHERE created_at > NOW() - INTERVAL '24 hours'
  GROUP BY source_ip
  ORDER BY request_count DESC;"
```

### PCI Compliance (for payment IVR)
```bash
# Enable PCI mode
export PCI_COMPLIANCE_MODE=true
export MASK_SENSITIVE_DATA=true
export RECORDING_PAUSE_ON_PAYMENT=true
pm2 restart twilio-server --update-env

# Audit sensitive data exposure
grep -r "credit\|card\|cvv\|ssn" /home/nevermisscall/.pm2/logs/

# Generate compliance report
node scripts/generate-pci-report.js --output /reports/pci-$(date +%Y%m).pdf
```

## Contact Information

- **Service Owner**: Communications Team
- **Primary Oncall**: twilio-oncall@nevermisscall.com
- **Escalation**: platform-oncall@nevermisscall.com
- **Twilio Support**: support@twilio.com
- **Slack Channel**: #twilio-server-alerts
- **PagerDuty**: twilio-server-critical

## Related Documentation

- [Twilio Integration Guide](./twilio-integration.md)
- [Webhook Documentation](./webhooks.md)
- [Call Flow Diagrams](./call-flows.md)
- [SMS Best Practices](./sms-guide.md)
- [Recording Management](./recordings.md)