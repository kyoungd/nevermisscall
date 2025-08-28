# NeverMissCall Web Dashboard

A modern, responsive web dashboard for managing call operations and customer interactions. Built with React, Next.js, and TypeScript.

## Quick Start

1. **Install dependencies**
   ```bash
   pnpm install
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your API endpoints
   ```

3. **Start development server**
   ```bash
   pnpm dev
   ```

4. **Open your browser**
   Navigate to [http://localhost:3000](http://localhost:3000)

## Demo Credentials

For testing purposes:
- **Email:** demo@nevermisscall.com
- **Password:** demo123

## Features

- 📞 **Real-time Call Monitoring** - Live call status and management
- 💬 **Conversation Management** - Handle customer conversations with AI takeover
- 📊 **Analytics Dashboard** - Comprehensive call and conversation analytics  
- ⚙️ **Settings Management** - User profiles, notifications, and preferences
- 🌙 **Dark/Light Theme** - Customizable appearance with system sync
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile
- 🔔 **Real-time Notifications** - Live updates via WebSocket connections

## Technology Stack

- **Framework:** Next.js 14 with App Router
- **UI Library:** React 18 with TypeScript
- **Styling:** Tailwind CSS + shadcn/ui components
- **State Management:** Zustand
- **Real-time:** Socket.IO
- **Forms:** React Hook Form + Zod validation
- **Testing:** Jest + React Testing Library

## API Integration

Connects to NeverMissCall microservices:
- Authentication Service (port 3301)
- Call Service (port 3304) 
- Tenant Service (port 3302)
- User Service (port 3303)
- Phone Number Service (port 3501)
- Connection Service (port 3105) - WebSocket

## Development

```bash
# Development server
pnpm dev

# Production build
pnpm build

# Run tests
pnpm test

# Lint code
pnpm lint

# Type checking
pnpm type-check
```

## Project Structure

```
src/
├── app/                 # Next.js pages and layouts
├── components/          # Reusable React components
├── lib/                # Utilities and configurations
├── store/              # Zustand state management
├── types/              # TypeScript definitions
└── hooks/              # Custom React hooks
```

## Documentation

See [CLAUDE.md](./CLAUDE.md) for detailed technical documentation including:
- Complete architecture overview
- API integration patterns
- Component structure
- State management patterns
- Security considerations
- Deployment instructions

## Environment Variables

Key environment variables needed:

```env
NEXT_PUBLIC_AUTH_API_URL=http://localhost:3301
NEXT_PUBLIC_CALL_API_URL=http://localhost:3304
NEXT_PUBLIC_SOCKET_URL=http://localhost:3105
NEXTAUTH_SECRET=your-secret-key
JWT_SECRET=your-jwt-secret
```

See `.env.example` for the complete list.

## Contributing

1. Follow TypeScript strict mode
2. Use existing component patterns
3. Add tests for new features
4. Ensure accessibility compliance
5. Update documentation for significant changes

## License

Part of the NeverMissCall platform. All rights reserved.