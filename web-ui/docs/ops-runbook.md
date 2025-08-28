# web-ui Operations Runbook

## Service Overview
The Web UI provides the frontend interface for NeverMissCall, built with Next.js. It handles user interactions, real-time updates, and serves as the primary customer-facing application.

## Environments

| Environment | URL | Port | Purpose |
|------------|-----|------|---------|  
| Development | http://localhost:3000 | 3000 | Local development |
| Staging | https://staging.nevermisscall.com | 3000 | Pre-production |
| Production | https://app.nevermisscall.com | 3000 | Live environment |

### Environment Variables
```bash
NODE_ENV=production
PORT=3000
NEXT_PUBLIC_API_URL=https://api.nevermisscall.com
NEXT_PUBLIC_WS_URL=wss://api.nevermisscall.com
NEXT_PUBLIC_GOOGLE_MAPS_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
REVALIDATE_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ENABLE_PWA=true
LOG_LEVEL=info
```

## Deployment

### Deploy Steps
```bash
# 1. Pull and build
cd /home/nevermisscall/nmc-main/web-ui
git pull origin main
pnpm install --frozen-lockfile

# 2. Build Next.js app
pnpm build

# 3. Optimize assets
pnpm optimize

# 4. Clear CDN cache
curl -X POST https://cdn.nevermisscall.com/api/purge \
  -H "Authorization: Bearer $CDN_TOKEN"

# 5. Reload service
pm2 reload web-ui

# 6. Verify deployment
curl -I https://app.nevermisscall.com
curl https://app.nevermisscall.com/api/health
```

### Rollback Steps
```bash
# 1. Revert to previous build
cd /home/nevermisscall/nmc-main/web-ui
git checkout $(git rev-parse HEAD~1)

# 2. Rebuild
pnpm install --frozen-lockfile
pnpm build

# 3. Restart
pm2 restart web-ui

# 4. Clear browser cache
curl -X POST https://app.nevermisscall.com/api/cache/clear
```

## Monitoring & Alerts

### Key Metrics
| Metric | Threshold | Alert Level | Action |
|--------|-----------|-------------|--------|
| Page Load Time | > 3s | WARNING | Check bundle size |
| JS Error Rate | > 1% | WARNING | Check Sentry |
| API Timeout Rate | > 5% | CRITICAL | Check backend services |
| Memory Usage | > 400MB | WARNING | Check for memory leaks |
| Core Web Vitals LCP | > 2.5s | WARNING | Optimize images/fonts |

## Common Incidents & Fixes

### 1. Slow Page Load
```bash
# Analyze bundle size
pnpm analyze

# Check largest modules
du -sh .next/static/chunks/* | sort -rh | head -10

# Enable aggressive caching
export CACHE_CONTROL_MAX_AGE=31536000
pm2 restart web-ui --update-env

# Optimize images
pnpm next-optimized-images
```

### 2. WebSocket Connection Issues
```bash
# Check WebSocket endpoint
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: SGVsbG8sIHdvcmxkIQ==" \
  https://api.nevermisscall.com/socket.io/

# Enable WebSocket fallback
export NEXT_PUBLIC_WS_FALLBACK=polling
pm2 restart web-ui --update-env
```

### 3. Authentication Issues
```bash
# Clear session storage
redis-cli --scan --pattern "sess:*" | xargs redis-cli DEL

# Verify JWT secret matches auth service
echo $JWT_SECRET | head -c 20

# Force re-authentication
curl -X POST https://app.nevermisscall.com/api/auth/logout-all \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### 4. Static Asset 404s
```bash
# Rebuild static assets
pnpm build

# Verify asset generation
ls -la .next/static/

# Sync to CDN
aws s3 sync .next/static/ s3://nevermisscall-static/

# Invalidate CDN
aws cloudfront create-invalidation \
  --distribution-id ABCDEFG \
  --paths "/*"
```

## Performance Optimization

```bash
# Enable production optimizations
export NODE_ENV=production
export NEXT_TELEMETRY_DISABLED=1

# Optimize for production
pnpm build
pnpm start

# Enable SWC minification
export NEXT_PUBLIC_SWC_MINIFY=true

# Preload critical resources
export NEXT_PUBLIC_PRELOAD_FONTS=true
export NEXT_PUBLIC_PRELOAD_IMAGES=true

pm2 restart web-ui --update-env
```

## SEO & Analytics

```bash
# Generate sitemap
pnpm generate-sitemap

# Submit to search engines
curl -X POST "https://www.google.com/ping?sitemap=https://app.nevermisscall.com/sitemap.xml"

# Verify analytics tracking
curl https://app.nevermisscall.com | grep -E "gtag|analytics"
```

## PWA Management

```bash
# Update service worker
pnpm generate-sw

# Clear old caches
curl -X POST https://app.nevermisscall.com/api/sw/clear-cache

# Test offline mode
pnpm test:offline
```

## Backup & Restore

```bash
# Backup build artifacts
tar czf /backup/web-ui-build-$(date +%Y%m%d).tar.gz \
  .next/ public/ package.json next.config.js

# Backup user uploads
rsync -av public/uploads/ /backup/uploads/$(date +%Y%m%d)/
```

## Disaster Recovery

- **RPO**: Near zero (stateless frontend)
- **RTO**: 5 minutes

### Static Site Fallback
```bash
# 1. Export static site
pnpm build && pnpm export

# 2. Deploy to CDN
aws s3 sync out/ s3://nevermisscall-static-site/

# 3. Update DNS to point to CDN
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://dns-failover.json
```

## Browser Compatibility

```bash
# Run compatibility tests
pnpm test:browsers

# Check browser console errors
pnpm analyze:errors --browser chrome,firefox,safari,edge

# Generate compatibility report
pnpm compat-report
```

## Contact Information

- **Service Owner**: Frontend Team
- **Oncall**: frontend-oncall@nevermisscall.com
- **Slack**: #web-ui-alerts
- **Design Team**: design@nevermisscall.com
- **PagerDuty**: web-ui-critical