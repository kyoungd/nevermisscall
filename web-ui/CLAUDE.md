# Web UI - NeverMissCall Dashboard

This is the customer-facing dashboard web application for the NeverMissCall platform. Built with React, Next.js, and modern web technologies to provide a professional, real-time call management interface.

## Overview

The web-ui is a comprehensive dashboard that allows businesses to:
- Monitor active calls and conversations in real-time
- Manage customer interactions with manual AI takeover capabilities
- View analytics and call history
- Configure phone numbers and business settings
- Manage team members and access controls

## Technology Stack

### Core Framework
- **Next.js 14+** - React framework with App Router, SSR, and API routes
- **React 18** - Modern React with hooks and concurrent features
- **TypeScript** - Type-safe development with strict mode

### Styling & UI
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Modern, accessible component library
- **Radix UI** - Unstyled, accessible UI primitives
- **Lucide React** - Beautiful icon library
- **next-themes** - Theme switching support

### State Management
- **Zustand** - Lightweight state management with TypeScript support
- **React Hook Form** - Performant forms with validation
- **Zod** - Schema validation

### Real-time & API
- **Socket.IO Client** - Real-time WebSocket communication
- **Axios** - HTTP client with interceptors
- **React Query** - Server state management (planned)

## Workspace Configuration
**IMPORTANT**: This service is part of the pnpm workspace but uses Next.js testing setup.

- **Package Manager**: pnpm workspace (configured at root level)
- **Testing Framework**: Jest with Next.js configuration (no tests currently implemented)
- **TypeScript**: Configured globally in workspace root
- **Build Tools**: Next.js build system

This service is included in the pnpm workspace but currently has no test files. When tests are added, they will use Next.js testing patterns rather than the standard TypeScript service testing configuration.

### Development Tools
- **ESLint** - Code linting with TypeScript rules
- **Jest** - Unit testing framework
- **Testing Library** - Component testing utilities

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── (dashboard)/       # Protected dashboard routes
│   │   ├── dashboard/     # Main dashboard page
│   │   ├── calls/         # Call management
│   │   ├── conversations/ # Conversation management
│   │   └── settings/      # Settings pages
│   ├── login/             # Authentication pages
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── layout/           # Layout components (Header, Sidebar)
│   ├── forms/            # Form components
│   ├── charts/           # Data visualization
│   └── providers/        # Context providers
├── hooks/                # Custom React hooks
├── lib/                  # Utility libraries
│   ├── api-client.ts     # API client configuration
│   ├── socket.ts         # Socket.IO client
│   └── utils.ts          # Helper utilities
├── store/                # Zustand stores
│   ├── auth.ts           # Authentication state
│   ├── calls.ts          # Calls and conversations state
│   └── ui.ts             # UI state
├── types/                # TypeScript type definitions
│   ├── auth.ts           # Authentication types
│   ├── calls.ts          # Call and conversation types
│   ├── tenant.ts         # Tenant and business types
│   └── api.ts            # API response types
├── utils/                # Utility functions
└── config/               # Configuration files
```

## Key Features

### 1. Authentication System
- JWT-based authentication with automatic token refresh
- Role-based access control (Owner, Operator, Viewer)
- Secure session management
- Password reset functionality

### 2. Real-time Dashboard
- Live call status monitoring with WebSocket updates
- Real-time conversation notifications
- System health indicators
- Automatic data refresh with configurable intervals

### 3. Call Management
- Complete call history with search and filtering
- Call recording playback (when available)
- Call analytics and metrics
- Export functionality for reporting

### 4. Conversation Management
- Active conversation monitoring
- Manual AI takeover capability
- Conversation history and message threads
- Note-taking and tagging system
- Priority and status management

### 5. User Interface
- Responsive design for desktop and mobile
- Dark/light theme support
- Accessible components (WCAG 2.1 AA compliant)
- Modern, intuitive design with loading states
- Toast notifications for user feedback

### 6. Settings & Configuration
- User profile management
- Notification preferences
- Theme customization
- Security settings
- Business hours configuration

## API Integration

The dashboard integrates with multiple microservices:

### Authentication Service (3301)
- User authentication and session management
- Password reset and security features
- JWT token management

### Tenant Service (3302)
- Business information and settings
- Subscription and billing data
- Multi-tenant configuration

### User Service (3303)
- User profiles and preferences
- Team member management
- Role and permission handling

### Call Service (3304)
- Call and conversation data
- Real-time call monitoring
- Analytics and reporting

### Phone Number Service (3501)
- Provisioned phone numbers
- Number management and configuration
- Carrier information

### Connection Service (3105)
- WebSocket real-time updates
- Event streaming
- Live dashboard data

## Environment Configuration

### Required Environment Variables

```env
# Application
NEXT_PUBLIC_APP_NAME=NeverMissCall Dashboard
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_APP_URL=http://localhost:3000

# API Endpoints
NEXT_PUBLIC_AUTH_API_URL=http://localhost:3301
NEXT_PUBLIC_TENANT_API_URL=http://localhost:3302
NEXT_PUBLIC_USER_API_URL=http://localhost:3303
NEXT_PUBLIC_CALL_API_URL=http://localhost:3304
NEXT_PUBLIC_PHONE_API_URL=http://localhost:3501
NEXT_PUBLIC_CONNECTION_API_URL=http://localhost:3105

# WebSocket
NEXT_PUBLIC_SOCKET_URL=http://localhost:3105

# Security
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
JWT_SECRET=your-jwt-secret

# Features
NEXT_PUBLIC_ENABLE_MANUAL_TAKEOVER=true
NEXT_PUBLIC_ENABLE_CALL_RECORDING=false
NEXT_PUBLIC_MAX_FILE_SIZE=5242880
```

## Development Commands

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Run tests
pnpm test

# Run linting
pnpm lint

# Type checking
pnpm type-check
```

## Component Architecture

### State Management Pattern
- **Global State**: Authentication, UI preferences, theme
- **Feature State**: Calls, conversations, dashboard metrics
- **Local State**: Form data, component-specific state
- **Server State**: API data with caching (future: React Query)

### Component Hierarchy
```
App Layout
├── AuthProvider (authentication context)
├── SocketProvider (real-time connections)
├── ThemeProvider (theme management)
└── ToastProvider (notifications)
    ├── Sidebar (navigation)
    ├── Header (user actions, search)
    └── Main Content
        ├── Dashboard (overview)
        ├── Calls (call management)
        ├── Conversations (chat interface)
        └── Settings (configuration)
```

### Real-time Updates
- Socket.IO connection with automatic reconnection
- Event-driven state updates for calls and conversations
- Optimistic UI updates with server confirmation
- Real-time notification system

## Security Considerations

### Client-side Security
- JWT tokens stored in secure localStorage with expiration checks
- Automatic token refresh before expiration
- XSS protection with Content Security Policy headers
- CSRF protection for state-changing operations

### API Security
- Bearer token authentication for all API calls
- Automatic logout on authentication failures
- Request/response interceptors for token management
- Secure HTTP headers (X-Frame-Options, X-Content-Type-Options)

## Performance Optimizations

### Bundle Optimization
- Code splitting by route and feature
- Dynamic imports for heavy components
- Tree shaking for unused code elimination
- Image optimization with Next.js Image component

### Runtime Performance
- React.memo for expensive components
- useCallback/useMemo for expensive calculations
- Virtual scrolling for large lists (future enhancement)
- Debounced search inputs

### Caching Strategy
- Static assets cached at CDN level
- API responses cached with appropriate TTL
- Local state persistence for user preferences
- Service worker for offline functionality (future enhancement)

## Testing Strategy

### Unit Testing
- Component testing with React Testing Library
- Store testing with Zustand test utilities
- Utility function testing with Jest
- API client mocking for isolated tests

### Integration Testing
- User flow testing with Playwright
- API integration testing
- Real-time feature testing
- Cross-browser compatibility testing

### E2E Testing
- Critical user paths (login, call management)
- Real-time functionality verification
- Mobile responsiveness testing
- Accessibility testing with automated tools

## Deployment

### Production Build
```bash
# Create optimized production build
pnpm build

# Start production server
pnpm start
```

### Docker Deployment
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build
EXPOSE 3000
CMD ["pnpm", "start"]
```

### Environment Setup
1. Copy `.env.example` to `.env.local`
2. Configure API endpoints for your environment
3. Set secure secrets for authentication
4. Enable required features with feature flags

## Future Enhancements

### Planned Features
- Advanced analytics dashboard with charts
- Call recording playback interface
- Advanced search with filters
- Bulk operations for conversation management
- Mobile app with React Native
- PWA capabilities for offline use

### Technical Improvements
- React Query for server state management
- Virtual scrolling for performance
- Advanced error boundary implementation
- Comprehensive logging and monitoring
- A11y improvements and WCAG 2.1 AAA compliance

## Troubleshooting

### Common Issues

**WebSocket Connection Fails**
- Check NEXT_PUBLIC_SOCKET_URL environment variable
- Verify connection service is running on port 3105
- Check browser console for CORS errors

**Authentication Errors**
- Verify JWT_SECRET matches across all services
- Check token expiration in localStorage
- Ensure auth service is running on port 3301

**Build Errors**
- Run `pnpm install` to update dependencies
- Check TypeScript errors with `pnpm type-check`
- Verify all environment variables are set

### Development Tips
- Use React DevTools for component debugging
- Check Network tab for API request issues
- Use browser console for real-time event debugging
- Monitor WebSocket connections in DevTools

## Contributing

When making changes to the web-ui:

1. **Follow TypeScript strict mode** - All code must be type-safe
2. **Use existing patterns** - Follow established component and state patterns
3. **Test thoroughly** - Add tests for new features and bug fixes
4. **Document changes** - Update this README for significant changes
5. **Review accessibility** - Ensure all UI changes meet accessibility standards

## Integration with NeverMissCall Platform

This web-ui is designed to work seamlessly with the NeverMissCall microservices architecture:

- **Stateless Design** - No server-side sessions, fully API-driven
- **Multi-tenant Ready** - Supports multiple business customers
- **Scalable Architecture** - Can be deployed across multiple servers
- **Real-time Capable** - Handles high-frequency updates efficiently
- **Security First** - Implements enterprise-level security practices

The dashboard serves as the primary interface for business customers to manage their call operations, monitor AI performance, and handle customer interactions when needed.