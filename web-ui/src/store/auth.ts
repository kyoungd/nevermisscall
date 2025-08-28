import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User, AuthTokens, LoginRequest, LoginResponse } from '@/types/auth'
import { apiClient } from '@/lib/api-client'

interface AuthState {
  user: User | null
  tokens: AuthTokens | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  updateUser: (updates: Partial<User>) => void
  clearError: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState & AuthActions>()(
  persist(
    (set, get) => ({
      // State
      user: null,
      tokens: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginRequest) => {
        try {
          set({ isLoading: true, error: null })
          
          const response = await apiClient.post<LoginResponse>('/auth/login', credentials)
          
          if (response.data.success && response.data.data) {
            const { user, tokens } = response.data.data
            
            set({
              user,
              tokens,
              isAuthenticated: true,
              isLoading: false,
              error: null
            })

            // Set up token refresh timer
            if (tokens.expiresAt) {
              const expirationTime = new Date(tokens.expiresAt).getTime()
              const currentTime = Date.now()
              const refreshTime = expirationTime - currentTime - 300000 // Refresh 5 minutes before expiry
              
              if (refreshTime > 0) {
                setTimeout(() => {
                  get().refreshToken()
                }, refreshTime)
              }
            }
          } else {
            throw new Error(response.data.error?.message || 'Login failed')
          }
        } catch (error: any) {
          const errorMessage = error.response?.data?.error?.message || error.message || 'Login failed'
          set({ 
            error: errorMessage, 
            isLoading: false,
            isAuthenticated: false,
            user: null,
            tokens: null
          })
          throw error
        }
      },

      logout: () => {
        set({
          user: null,
          tokens: null,
          isAuthenticated: false,
          error: null
        })
        
        // Call logout endpoint to invalidate server-side session
        apiClient.post('/auth/logout').catch(() => {
          // Ignore errors during logout
        })
      },

      refreshToken: async () => {
        try {
          const { tokens } = get()
          if (!tokens?.refreshToken) {
            throw new Error('No refresh token available')
          }

          const response = await apiClient.post('/auth/refresh', {
            refreshToken: tokens.refreshToken
          })

          if (response.data.success && response.data.data) {
            const newTokens = {
              ...tokens,
              accessToken: response.data.data.accessToken,
              expiresAt: new Date(response.data.data.expiresAt)
            }

            set({ tokens: newTokens })

            // Set up next refresh timer
            const expirationTime = newTokens.expiresAt.getTime()
            const currentTime = Date.now()
            const refreshTime = expirationTime - currentTime - 300000

            if (refreshTime > 0) {
              setTimeout(() => {
                get().refreshToken()
              }, refreshTime)
            }
          } else {
            throw new Error('Token refresh failed')
          }
        } catch (error) {
          console.error('Token refresh failed:', error)
          // If refresh fails, logout user
          get().logout()
        }
      },

      updateUser: (updates: Partial<User>) => {
        const { user } = get()
        if (user) {
          set({
            user: { ...user, ...updates }
          })
        }
      },

      clearError: () => {
        set({ error: null })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      }
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        tokens: state.tokens,
        isAuthenticated: state.isAuthenticated
      }),
      onRehydrateStorage: () => (state) => {
        // Check token expiration on rehydration
        if (state?.tokens?.expiresAt) {
          const expirationTime = new Date(state.tokens.expiresAt).getTime()
          const currentTime = Date.now()
          
          if (currentTime >= expirationTime) {
            // Token expired, logout
            state.logout()
          } else {
            // Set up refresh timer
            const refreshTime = expirationTime - currentTime - 300000
            if (refreshTime > 0) {
              setTimeout(() => {
                state.refreshToken()
              }, refreshTime)
            }
          }
        }
      }
    }
  )
)