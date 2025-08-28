// API response and request types

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: ApiError
  meta?: ResponseMeta
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, any>
  field?: string
  timestamp: string
}

export interface ResponseMeta {
  pagination?: PaginationMeta
  totalCount?: number
  page?: number
  limit?: number
  hasNext?: boolean
  hasPrevious?: boolean
}

export interface PaginationMeta {
  currentPage: number
  totalPages: number
  totalCount: number
  limit: number
  hasNext: boolean
  hasPrevious: boolean
}

export interface PaginatedRequest {
  page?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface SearchRequest extends PaginatedRequest {
  query?: string
  filters?: Record<string, any>
}

// Specific API request/response types
export interface CallListRequest extends PaginatedRequest {
  status?: string[]
  direction?: string[]
  dateFrom?: string
  dateTo?: string
  phoneNumber?: string
  hasRecording?: boolean
}

export interface ConversationListRequest extends PaginatedRequest {
  status?: string[]
  priority?: string[]
  assignedTo?: string
  dateFrom?: string
  dateTo?: string
  tags?: string[]
}

export interface UserListRequest extends PaginatedRequest {
  role?: string[]
  status?: string[]
  search?: string
}

export interface PhoneNumberListRequest extends PaginatedRequest {
  type?: string[]
  status?: string[]
  region?: string
}

// WebSocket event types
export interface WebSocketEvent<T = any> {
  type: string
  data: T
  timestamp: string
  tenantId?: string
  userId?: string
}

export interface CallUpdateEvent {
  callId: string
  status: string
  participants?: any[]
  duration?: number
  endTime?: string
}

export interface ConversationUpdateEvent {
  conversationId: string
  status: string
  priority?: string
  assignedTo?: string
  newMessage?: any
}

export interface SystemNotificationEvent {
  id: string
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
  actions?: NotificationAction[]
  persistent?: boolean
}

export interface NotificationAction {
  label: string
  action: string
  variant?: 'default' | 'primary' | 'destructive'
}

// File upload types
export interface FileUploadRequest {
  file: File
  type: 'avatar' | 'logo' | 'document'
  metadata?: Record<string, any>
}

export interface FileUploadResponse {
  id: string
  filename: string
  originalName: string
  mimeType: string
  size: number
  url: string
  thumbnailUrl?: string
  uploadedAt: string
}

// Health check and system status
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  version: string
  uptime: number
  services: ServiceHealth[]
  metrics: SystemMetrics
}

export interface ServiceHealth {
  name: string
  status: 'up' | 'down' | 'degraded'
  responseTime?: number
  lastCheck: string
  message?: string
}

export interface SystemMetrics {
  memoryUsage: number
  cpuUsage: number
  diskUsage: number
  activeConnections: number
  requestsPerMinute: number
}

// Analytics and reporting
export interface AnalyticsRequest {
  dateFrom: string
  dateTo: string
  granularity: 'hour' | 'day' | 'week' | 'month'
  metrics: string[]
  filters?: Record<string, any>
}

export interface AnalyticsResponse {
  metrics: AnalyticsMetric[]
  summary: AnalyticsSummary
  period: {
    from: string
    to: string
    granularity: string
  }
}

export interface AnalyticsMetric {
  name: string
  data: DataPoint[]
  unit: string
  description: string
}

export interface DataPoint {
  timestamp: string
  value: number
  metadata?: Record<string, any>
}

export interface AnalyticsSummary {
  totalCalls: number
  totalMinutes: number
  averageCallDuration: number
  missedCallsRate: number
  customerSatisfaction?: number
  topPhoneNumbers: Array<{
    number: string
    callCount: number
    totalMinutes: number
  }>
}

// Export and import types
export interface ExportRequest {
  type: 'calls' | 'conversations' | 'users' | 'analytics'
  format: 'csv' | 'json' | 'xlsx'
  dateFrom?: string
  dateTo?: string
  filters?: Record<string, any>
  columns?: string[]
}

export interface ExportResponse {
  id: string
  status: 'processing' | 'completed' | 'failed'
  downloadUrl?: string
  filename?: string
  size?: number
  createdAt: string
  expiresAt: string
}