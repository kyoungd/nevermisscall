// Call and conversation related types

export interface Call {
  id: string
  tenantId: string
  fromNumber: string
  toNumber: string
  direction: CallDirection
  status: CallStatus
  startTime: Date
  endTime?: Date
  duration?: number
  recordingUrl?: string
  cost?: number
  metadata: CallMetadata
  participants: CallParticipant[]
  conversations: Conversation[]
  createdAt: Date
  updatedAt: Date
}

export enum CallDirection {
  INBOUND = 'inbound',
  OUTBOUND = 'outbound'
}

export enum CallStatus {
  RINGING = 'ringing',
  ACTIVE = 'active',
  COMPLETED = 'completed',
  FAILED = 'failed',
  BUSY = 'busy',
  NO_ANSWER = 'no_answer',
  CANCELLED = 'cancelled'
}

export interface CallMetadata {
  twilioCallSid?: string
  callerLocation?: {
    city?: string
    state?: string
    country?: string
  }
  callQuality?: {
    score?: number
    issues?: string[]
  }
  transferHistory?: CallTransfer[]
  notes?: string[]
  tags?: string[]
}

export interface CallParticipant {
  id: string
  number: string
  role: ParticipantRole
  joinedAt: Date
  leftAt?: Date
  status: ParticipantStatus
  muted?: boolean
  onHold?: boolean
}

export enum ParticipantRole {
  CALLER = 'caller',
  RECIPIENT = 'recipient',
  AI_ASSISTANT = 'ai_assistant',
  HUMAN_AGENT = 'human_agent'
}

export enum ParticipantStatus {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  RINGING = 'ringing',
  BUSY = 'busy'
}

export interface CallTransfer {
  id: string
  fromParticipant: string
  toParticipant: string
  reason: string
  timestamp: Date
  successful: boolean
}

export interface Conversation {
  id: string
  callId: string
  tenantId: string
  status: ConversationStatus
  priority: ConversationPriority
  subject?: string
  summary?: string
  startTime: Date
  endTime?: Date
  assignedTo?: string
  tags: string[]
  messages: ConversationMessage[]
  metadata: ConversationMetadata
  createdAt: Date
  updatedAt: Date
}

export enum ConversationStatus {
  ACTIVE = 'active',
  WAITING = 'waiting',
  RESOLVED = 'resolved',
  CLOSED = 'closed',
  ESCALATED = 'escalated'
}

export enum ConversationPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent'
}

export interface ConversationMessage {
  id: string
  conversationId: string
  sender: MessageSender
  content: string
  type: MessageType
  timestamp: Date
  metadata?: {
    confidence?: number
    intent?: string
    entities?: Record<string, any>
    sentiment?: 'positive' | 'negative' | 'neutral'
  }
}

export enum MessageSender {
  CALLER = 'caller',
  AI_ASSISTANT = 'ai_assistant',
  HUMAN_AGENT = 'human_agent',
  SYSTEM = 'system'
}

export enum MessageType {
  TEXT = 'text',
  AUDIO = 'audio',
  SYSTEM_ACTION = 'system_action',
  TRANSFER_REQUEST = 'transfer_request',
  APPOINTMENT_SCHEDULED = 'appointment_scheduled'
}

export interface ConversationMetadata {
  aiHandled: boolean
  humanTakeoverRequested: boolean
  humanTakeoverAt?: Date
  escalationReason?: string
  customerSatisfaction?: number
  appointmentScheduled?: {
    id: string
    datetime: Date
    service: string
    confirmed: boolean
  }
  businessInfo?: {
    hours?: string
    services?: string[]
    location?: string
  }
}

export interface CallFilters {
  status?: CallStatus[]
  direction?: CallDirection[]
  dateFrom?: Date
  dateTo?: Date
  phoneNumber?: string
  minDuration?: number
  maxDuration?: number
  hasRecording?: boolean
  hasConversation?: boolean
}

export interface ConversationFilters {
  status?: ConversationStatus[]
  priority?: ConversationPriority[]
  assignedTo?: string
  dateFrom?: Date
  dateTo?: Date
  tags?: string[]
  aiHandled?: boolean
  hasAppointment?: boolean
}

export interface CallStats {
  total: number
  active: number
  completed: number
  missed: number
  averageDuration: number
  totalDuration: number
  conversionRate: number
}

export interface ConversationStats {
  total: number
  active: number
  waiting: number
  resolved: number
  closed: number
  averageResponseTime: number
  aiHandleRate: number
  escalationRate: number
}

export interface DashboardStats {
  calls: CallStats
  conversations: ConversationStats
  phoneNumbers: {
    total: number
    active: number
    available: number
  }
  system: {
    uptime: number
    lastUpdate: Date
    status: 'healthy' | 'warning' | 'error'
  }
}