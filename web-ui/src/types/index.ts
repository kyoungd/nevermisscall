// Re-export all types for easy importing

export * from './auth'
export * from './calls'
export * from './tenant'
export * from './api'

// Common utility types
export interface SelectOption<T = string> {
  value: T
  label: string
  disabled?: boolean
  icon?: React.ComponentType<any>
}

export interface TableColumn<T = any> {
  key: string
  label: string
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
  render?: (value: any, record: T) => React.ReactNode
}

export interface FormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'file' | 'date' | 'time' | 'datetime'
  placeholder?: string
  required?: boolean
  disabled?: boolean
  options?: SelectOption[]
  validation?: {
    min?: number
    max?: number
    pattern?: string
    custom?: (value: any) => string | undefined
  }
  description?: string
  defaultValue?: any
}

export interface MenuItem {
  key: string
  label: string
  icon?: React.ComponentType<any>
  href?: string
  children?: MenuItem[]
  badge?: string | number
  disabled?: boolean
}

export interface BreadcrumbItem {
  label: string
  href?: string
  active?: boolean
}

export interface Toast {
  id: string
  title?: string
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  duration?: number
  persistent?: boolean
  actions?: Array<{
    label: string
    onClick: () => void
  }>
}

export interface Modal {
  id: string
  title: string
  content: React.ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  closable?: boolean
  persistent?: boolean
  onClose?: () => void
}

// Loading and error states
export interface LoadingState {
  isLoading: boolean
  error?: string | null
  lastUpdated?: Date
}

export interface AsyncState<T> extends LoadingState {
  data?: T | null
}

// Theme and UI preferences
export interface UIPreferences {
  theme: 'light' | 'dark' | 'system'
  sidebarCollapsed: boolean
  compactMode: boolean
  animations: boolean
  autoRefresh: boolean
  refreshInterval: number
}

// Chart and visualization types
export interface ChartData {
  labels: string[]
  datasets: ChartDataset[]
}

export interface ChartDataset {
  label: string
  data: number[]
  backgroundColor?: string | string[]
  borderColor?: string | string[]
  borderWidth?: number
  fill?: boolean
}

export interface ChartOptions {
  responsive: boolean
  maintainAspectRatio: boolean
  plugins?: {
    legend?: {
      display: boolean
      position?: 'top' | 'bottom' | 'left' | 'right'
    }
    tooltip?: {
      enabled: boolean
    }
  }
  scales?: {
    x?: {
      display: boolean
      title?: {
        display: boolean
        text: string
      }
    }
    y?: {
      display: boolean
      title?: {
        display: boolean
        text: string
      }
    }
  }
}

// Environment and configuration
export interface AppConfig {
  name: string
  version: string
  apiUrl: string
  wsUrl: string
  features: {
    manualTakeover: boolean
    callRecording: boolean
    analytics: boolean
    integrations: boolean
  }
  limits: {
    maxFileSize: number
    maxUploadFiles: number
    sessionTimeout: number
  }
}

// Event and action types for state management
export type Action<T = any> = {
  type: string
  payload?: T
}

export type Reducer<T> = (state: T, action: Action) => T

// Generic error type
export interface AppError {
  code: string
  message: string
  details?: any
  timestamp: Date
}