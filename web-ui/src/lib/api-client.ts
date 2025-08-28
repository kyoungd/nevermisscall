import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { useAuthStore } from '@/store/auth'

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().tokens?.accessToken
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    // Set base URL based on the endpoint
    if (config.url?.startsWith('/auth') || config.url?.startsWith('/users')) {
      config.baseURL = process.env.NEXT_PUBLIC_AUTH_API_URL
    } else if (config.url?.startsWith('/tenants')) {
      config.baseURL = process.env.NEXT_PUBLIC_TENANT_API_URL
    } else if (config.url?.startsWith('/calls') || config.url?.startsWith('/conversations')) {
      config.baseURL = process.env.NEXT_PUBLIC_CALL_API_URL
    } else if (config.url?.startsWith('/phone-numbers')) {
      config.baseURL = process.env.NEXT_PUBLIC_PHONE_API_URL
    } else if (config.url?.startsWith('/dashboard')) {
      config.baseURL = process.env.NEXT_PUBLIC_CALL_API_URL
    } else {
      // Default to auth service for generic endpoints
      config.baseURL = process.env.NEXT_PUBLIC_AUTH_API_URL
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling and token refresh
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      try {
        // Attempt to refresh token
        await useAuthStore.getState().refreshToken()
        
        // Retry original request with new token
        const token = useAuthStore.getState().tokens?.accessToken
        if (token && originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${token}`
        }
        
        return apiClient(originalRequest)
      } catch (refreshError) {
        // Refresh failed, logout user
        useAuthStore.getState().logout()
        
        // Redirect to login page
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
        
        return Promise.reject(refreshError)
      }
    }
    
    return Promise.reject(error)
  }
)

// API service classes for different endpoints
export class AuthAPI {
  static async login(credentials: { email: string; password: string; rememberMe?: boolean }) {
    return apiClient.post('/auth/login', credentials)
  }
  
  static async logout() {
    return apiClient.post('/auth/logout')
  }
  
  static async refreshToken(refreshToken: string) {
    return apiClient.post('/auth/refresh', { refreshToken })
  }
  
  static async resetPassword(email: string) {
    return apiClient.post('/auth/reset-password', { email })
  }
  
  static async confirmPasswordReset(token: string, newPassword: string) {
    return apiClient.post('/auth/reset-password/confirm', { token, newPassword })
  }
  
  static async changePassword(currentPassword: string, newPassword: string) {
    return apiClient.post('/auth/change-password', { currentPassword, newPassword })
  }
}

export class UserAPI {
  static async getProfile() {
    return apiClient.get('/users/profile')
  }
  
  static async updateProfile(data: any) {
    return apiClient.patch('/users/profile', data)
  }
  
  static async updatePreferences(preferences: any) {
    return apiClient.patch('/users/preferences', preferences)
  }
  
  static async uploadAvatar(file: File) {
    const formData = new FormData()
    formData.append('avatar', file)
    
    return apiClient.post('/users/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }
}

export class TenantAPI {
  static async getTenant(id?: string) {
    const url = id ? `/tenants/${id}` : '/tenants/current'
    return apiClient.get(url)
  }
  
  static async updateTenant(id: string, data: any) {
    return apiClient.patch(`/tenants/${id}`, data)
  }
  
  static async getSettings() {
    return apiClient.get('/tenants/current/settings')
  }
  
  static async updateSettings(settings: any) {
    return apiClient.patch('/tenants/current/settings', settings)
  }
}

export class CallAPI {
  static async getCalls(params?: any) {
    return apiClient.get('/calls', { params })
  }
  
  static async getCall(id: string) {
    return apiClient.get(`/calls/${id}`)
  }
  
  static async getCallRecording(id: string) {
    return apiClient.get(`/calls/${id}/recording`)
  }
  
  static async exportCalls(params?: any) {
    return apiClient.post('/calls/export', params)
  }
}

export class ConversationAPI {
  static async getConversations(params?: any) {
    return apiClient.get('/conversations', { params })
  }
  
  static async getConversation(id: string) {
    return apiClient.get(`/conversations/${id}`)
  }
  
  static async requestTakeover(id: string) {
    return apiClient.post(`/conversations/${id}/takeover`)
  }
  
  static async updateStatus(id: string, status: string) {
    return apiClient.patch(`/conversations/${id}`, { status })
  }
  
  static async addNote(id: string, note: string) {
    return apiClient.post(`/conversations/${id}/notes`, { note })
  }
  
  static async addTag(id: string, tag: string) {
    return apiClient.post(`/conversations/${id}/tags`, { tag })
  }
  
  static async removeTag(id: string, tag: string) {
    return apiClient.delete(`/conversations/${id}/tags/${tag}`)
  }
}

export class DashboardAPI {
  static async getStats(params?: any) {
    return apiClient.get('/dashboard/stats', { params })
  }
  
  static async getRealtimeMetrics() {
    return apiClient.get('/dashboard/realtime')
  }
  
  static async getAnalytics(params: any) {
    return apiClient.get('/dashboard/analytics', { params })
  }
}

export class PhoneNumberAPI {
  static async getPhoneNumbers(params?: any) {
    return apiClient.get('/phone-numbers', { params })
  }
  
  static async getPhoneNumber(id: string) {
    return apiClient.get(`/phone-numbers/${id}`)
  }
  
  static async updatePhoneNumber(id: string, data: any) {
    return apiClient.patch(`/phone-numbers/${id}`, data)
  }
}

// Health check utility
export class HealthAPI {
  static async checkHealth() {
    return apiClient.get('/health')
  }
  
  static async getSystemStatus() {
    return apiClient.get('/system/status')
  }
}

// File upload utility
export class FileAPI {
  static async upload(file: File, type: string = 'document') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('type', type)
    
    return apiClient.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 60000 // 1 minute for file uploads
    })
  }
  
  static async delete(id: string) {
    return apiClient.delete(`/files/${id}`)
  }
}

// Export default instance for general use
export default apiClient