// Tenant and organizational types

export interface Tenant {
  id: string
  name: string
  domain: string
  status: TenantStatus
  settings: TenantSettings
  subscription: TenantSubscription
  businessInfo: BusinessInfo
  phoneNumbers: PhoneNumber[]
  integrations: Integration[]
  createdAt: Date
  updatedAt: Date
}

export enum TenantStatus {
  ACTIVE = 'active',
  SUSPENDED = 'suspended',
  PENDING = 'pending',
  CANCELLED = 'cancelled'
}

export interface TenantSettings {
  timezone: string
  businessHours: BusinessHours
  callHandling: CallHandlingSettings
  notifications: NotificationSettings
  branding: BrandingSettings
  security: SecuritySettings
}

export interface BusinessHours {
  monday: DaySchedule
  tuesday: DaySchedule
  wednesday: DaySchedule
  thursday: DaySchedule
  friday: DaySchedule
  saturday: DaySchedule
  sunday: DaySchedule
  holidays: Holiday[]
}

export interface DaySchedule {
  isOpen: boolean
  openTime?: string // HH:mm format
  closeTime?: string // HH:mm format
  breaks?: TimeSlot[]
}

export interface TimeSlot {
  startTime: string // HH:mm format
  endTime: string // HH:mm format
}

export interface Holiday {
  id: string
  name: string
  date: Date
  isRecurring: boolean
}

export interface CallHandlingSettings {
  maxRingTime: number
  enableVoicemail: boolean
  voicemailGreeting?: string
  enableCallRecording: boolean
  autoAnswer: boolean
  transferTimeout: number
  maxCallDuration: number
  allowInternationalCalls: boolean
}

export interface NotificationSettings {
  missedCalls: {
    email: boolean
    sms: boolean
    webhook?: string
  }
  newConversations: {
    email: boolean
    sms: boolean
    realtime: boolean
  }
  systemAlerts: {
    email: boolean
    sms: boolean
  }
  dailyReports: {
    enabled: boolean
    time: string // HH:mm format
    recipients: string[]
  }
}

export interface BrandingSettings {
  companyName: string
  logo?: string
  primaryColor: string
  secondaryColor: string
  customDomain?: string
  whiteLabel: boolean
}

export interface SecuritySettings {
  twoFactorAuth: boolean
  sessionTimeout: number
  ipRestrictions: string[]
  allowedDomains: string[]
  auditLogging: boolean
}

export interface TenantSubscription {
  plan: SubscriptionPlan
  status: SubscriptionStatus
  billingCycle: BillingCycle
  currentPeriodStart: Date
  currentPeriodEnd: Date
  trialEnd?: Date
  usage: UsageMetrics
  limits: SubscriptionLimits
}

export enum SubscriptionPlan {
  FREE = 'free',
  STARTER = 'starter',
  PROFESSIONAL = 'professional',
  ENTERPRISE = 'enterprise'
}

export enum SubscriptionStatus {
  ACTIVE = 'active',
  CANCELLED = 'cancelled',
  PAST_DUE = 'past_due',
  TRIALING = 'trialing'
}

export enum BillingCycle {
  MONTHLY = 'monthly',
  YEARLY = 'yearly'
}

export interface UsageMetrics {
  callMinutes: number
  phoneNumbers: number
  users: number
  storage: number // in MB
  apiCalls: number
}

export interface SubscriptionLimits {
  maxCallMinutes: number
  maxPhoneNumbers: number
  maxUsers: number
  maxStorage: number // in MB
  maxApiCalls: number
  features: {
    callRecording: boolean
    advancedAnalytics: boolean
    customIntegrations: boolean
    whiteLabel: boolean
    prioritySupport: boolean
  }
}

export interface BusinessInfo {
  industry: string
  companySize: CompanySize
  website?: string
  address: Address
  primaryContact: Contact
  taxInfo?: TaxInfo
}

export enum CompanySize {
  SOLO = 'solo',
  SMALL = 'small', // 2-10 employees
  MEDIUM = 'medium', // 11-50 employees
  LARGE = 'large', // 51+ employees
}

export interface Address {
  street: string
  city: string
  state: string
  postalCode: string
  country: string
}

export interface Contact {
  firstName: string
  lastName: string
  email: string
  phone: string
  role: string
}

export interface TaxInfo {
  taxId?: string
  vatNumber?: string
  exemptFromTax: boolean
}

export interface PhoneNumber {
  id: string
  number: string
  friendlyName?: string
  type: PhoneNumberType
  status: PhoneNumberStatus
  capabilities: PhoneNumberCapabilities
  assignedTo?: string
  purchaseDate: Date
  monthlyFee: number
  region: string
}

export enum PhoneNumberType {
  LOCAL = 'local',
  TOLL_FREE = 'toll_free',
  SHORT_CODE = 'short_code'
}

export enum PhoneNumberStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  PENDING = 'pending',
  SUSPENDED = 'suspended'
}

export interface PhoneNumberCapabilities {
  voice: boolean
  sms: boolean
  mms: boolean
  fax: boolean
}

export interface Integration {
  id: string
  type: IntegrationType
  name: string
  status: IntegrationStatus
  config: Record<string, any>
  lastSync?: Date
  createdAt: Date
}

export enum IntegrationType {
  CRM = 'crm',
  CALENDAR = 'calendar',
  EMAIL = 'email',
  WEBHOOK = 'webhook',
  ZAPIER = 'zapier'
}

export enum IntegrationStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error',
  PENDING = 'pending'
}