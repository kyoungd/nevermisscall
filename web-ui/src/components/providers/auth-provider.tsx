'use client'

import React, { createContext, useContext, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'

interface AuthContextType {
  isLoading: boolean
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType>({
  isLoading: true,
  isAuthenticated: false,
})

export function useAuth() {
  return useContext(AuthContext)
}

interface AuthProviderProps {
  children: React.ReactNode
}

const publicPaths = ['/login', '/reset-password', '/signup', '/']
const authPaths = ['/login', '/reset-password', '/signup']

export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, isLoading, user, tokens } = useAuthStore()
  const { setGlobalLoading } = useUIStore()
  const [initialCheckDone, setInitialCheckDone] = React.useState(false)

  useEffect(() => {
    // Check if we need to redirect based on auth state
    const checkAuthAndRedirect = () => {
      const isPublicPath = publicPaths.includes(pathname)
      const isAuthPath = authPaths.includes(pathname)

      if (!isAuthenticated) {
        // User is not authenticated
        if (!isPublicPath && !isLoading) {
          // Redirect to login if trying to access protected route
          router.push('/login')
        }
      } else {
        // User is authenticated
        if (isAuthPath) {
          // Redirect away from auth pages if already logged in
          router.push('/dashboard')
        }
      }

      setInitialCheckDone(true)
    }

    // Only check after the initial loading is done
    if (!isLoading) {
      checkAuthAndRedirect()
    }
  }, [isAuthenticated, isLoading, pathname, router])

  // Token expiration check
  useEffect(() => {
    if (tokens?.expiresAt) {
      const checkTokenExpiration = () => {
        const expirationTime = new Date(tokens.expiresAt).getTime()
        const currentTime = Date.now()
        const fiveMinutes = 5 * 60 * 1000

        if (currentTime >= expirationTime - fiveMinutes) {
          // Token is about to expire or has expired
          console.log('Token is about to expire, attempting refresh...')
          useAuthStore.getState().refreshToken()
        }
      }

      // Check immediately
      checkTokenExpiration()

      // Set up periodic check every minute
      const interval = setInterval(checkTokenExpiration, 60000)

      return () => clearInterval(interval)
    }
  }, [tokens])

  // Handle global loading state
  useEffect(() => {
    if (isLoading && !initialCheckDone) {
      setGlobalLoading(true, 'Checking authentication...')
    } else {
      setGlobalLoading(false)
    }
  }, [isLoading, initialCheckDone, setGlobalLoading])

  // Show loading screen while checking authentication
  if (isLoading || !initialCheckDone) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center space-y-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  const contextValue: AuthContextType = {
    isLoading,
    isAuthenticated,
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}