# Phase 1 Authentication Standards

## Authentication Patterns

### 1. User-Facing Endpoints
**Pattern**: `Authorization: Bearer jwt-token`
**Usage**: When web-ui calls services for user actions
**Examples**:
- `GET /conversations/:conversationId` 
- `POST /tenants/:tenantId/settings`
- `PUT /users/profile`

### 2. Service-to-Service Endpoints  
**Pattern**: `X-Service-Key: internal-service-key`
**Usage**: When services call each other internally
**Examples**:
- `POST /calls/incoming` (twilio-server → as-call-service)
- `POST /connections/broadcast` (as-call-service → as-connection-service)
- `GET /phone-numbers/lookup/:phoneNumber` (twilio-server → pns-provisioning-service)

### 3. Public/Webhook Endpoints
**Pattern**: No authentication (validated by signature/source)
**Usage**: External webhook endpoints
**Examples**:
- `POST /webhooks/twilio/call` (Twilio → twilio-server)
- `GET /health` (monitoring systems)

## Service Key Configuration

Each service that makes internal calls needs:
```bash
INTERNAL_SERVICE_KEY=shared-secret-key-for-phase-1
```

Each service that receives internal calls must validate this key.

## Implementation Standards

### JWT Token Validation
```javascript
const jwt = require('jsonwebtoken');

function validateJWT(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) return res.status(401).json({ error: 'Missing token' });
  
  try {
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
}
```

### Service Key Validation
```javascript
function validateServiceKey(req, res, next) {
  const serviceKey = req.headers['x-service-key'];
  if (!serviceKey || serviceKey !== process.env.INTERNAL_SERVICE_KEY) {
    return res.status(401).json({ error: 'Invalid service key' });
  }
  next();
}
```

## Error Responses

**Unauthorized (401)**:
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required"
  }
}
```

**Forbidden (403)**:
```json
{
  "success": false, 
  "error": {
    "code": "FORBIDDEN",
    "message": "Access denied"
  }
}
```