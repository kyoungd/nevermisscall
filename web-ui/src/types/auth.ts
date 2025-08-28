// Authentication and authorization types

export interface User {
  id: string
  tenantId: string
  email: string
  firstName: string
  lastName: string
  role: UserRole
  status: UserStatus
  avatar?: string
  phone?: string
  timezone?: string
  preferences: UserPreferences
  lastLogin?: Date
  createdAt: Date
  updatedAt: Date
}

export enum UserRole {
  OWNER = 'owner',
  OPERATOR = 'operator',
  VIEWER = 'viewer'
}

export enum UserStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  SUSPENDED = 'suspended'
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  notifications: {
    email: boolean
    push: boolean
    desktop: boolean
    sounds: boolean
  }
  dashboard: {
    autoRefresh: boolean
    refreshInterval: number
    defaultView: 'dashboard' | 'calls' | 'conversations'
  }
  calls: {
    showMissedOnly: boolean
    autoPlayRecordings: boolean
    groupByDate: boolean
  }
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresAt: Date
}

export interface LoginRequest {
  email: string
  password: string
  rememberMe?: boolean
}

export interface LoginResponse {
  user: User
  tokens: AuthTokens
  tenant: {
    id: string
    name: string
    domain: string
  }
}

export interface RefreshTokenRequest {
  refreshToken: string
}

export interface RefreshTokenResponse {
  accessToken: string
  expiresAt: Date
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirmRequest {
  token: string
  newPassword: string
}

export interface ChangePasswordRequest {
  currentPassword: string
  newPassword: string
}

export interface UpdateProfileRequest {
  firstName?: string
  lastName?: string
  phone?: string
  timezone?: string
  avatar?: string
}

export interface UpdatePreferencesRequest {
  theme?: 'light' | 'dark' | 'system'
  notifications?: {
    email?: boolean
    push?: boolean
    desktop?: boolean
    sounds?: boolean
  }
  dashboard?: {
    autoRefresh?: boolean
    refreshInterval?: number
    defaultView?: 'dashboard' | 'calls' | 'conversations'
  }
  calls?: {
    showMissedOnly?: boolean
    autoPlayRecordings?: boolean
    groupByDate?: boolean
  }
}