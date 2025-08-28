# Twilio-Server

Twilio integration service for call and SMS processing within the NeverMissCall platform.

## Quickstart

```bash
# Install dependencies
pnpm install

# Set environment variables
export NODE_ENV=development
export PORT=3500
export TWILIO_ACCOUNT_SID=your_twilio_sid
export TWILIO_AUTH_TOKEN=your_twilio_token

# Build and start
pnpm build
pnpm start
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| NODE_ENV | Environment mode | Yes | development |
| PORT | Service port | Yes | 3500 |
| TWILIO_ACCOUNT_SID | Twilio account identifier | Yes | - |
| TWILIO_AUTH_TOKEN | Twilio authentication token | Yes | - |
| TWILIO_PHONE_NUMBER | Twilio phone number | Yes | - |
| DATABASE_URL | PostgreSQL connection string | No | - |

## Tests

```bash
# Run tests
pnpm test

# Run with coverage
pnpm run test:coverage
```

## Deployment

```bash
# Build production
pnpm build

# Start production
NODE_ENV=production pnpm start
```

## Architecture

Twilio integration service providing webhook handling for missed calls, SMS conversation management, AI dispatcher logic, and real-time communication processing.

## Documentation

- [Service Documentation](./CLAUDE.md) - Complete service specification
- [API Reference](./docs/api/) - OpenAPI specifications
- [Architecture](./docs/architecture.md) - System design details