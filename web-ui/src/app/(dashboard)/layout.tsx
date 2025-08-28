'use client'

import React from 'react'
import { useAuthStore } from '@/store/auth'
import { useCallsStore } from '@/store/calls'
import { useUIStore } from '@/store/ui'
import { Sidebar } from '@/components/layout/sidebar'
import { Header } from '@/components/layout/header'
import { cn } from '@/lib/utils'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { isAuthenticated } = useAuthStore()
  const { sidebarCollapsed } = useUIStore()
  const { fetchDashboardStats, fetchCalls, fetchConversations } = useCallsStore()

  // Load initial data when component mounts
  React.useEffect(() => {
    if (isAuthenticated) {
      const loadData = async () => {
        try {
          await Promise.all([
            fetchDashboardStats(),
            fetchCalls({ limit: 10 }),
            fetchConversations({ limit: 10 })
          ])
        } catch (error) {
          console.error('Failed to load initial dashboard data:', error)
        }
      }

      loadData()

      // Set up periodic refresh
      const interval = setInterval(() => {
        fetchDashboardStats()
      }, 30000) // Refresh every 30 seconds

      return () => clearInterval(interval)
    }
  }, [isAuthenticated, fetchDashboardStats, fetchCalls, fetchConversations])

  if (!isAuthenticated) {
    return null // AuthProvider will handle redirect
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div
        className={cn(
          'transition-all duration-300',
          sidebarCollapsed ? 'ml-16' : 'ml-64'
        )}
      >
        <Header />
        <main className="pt-[120px]"> {/* Account for header + quick stats bar */}
          <div className="container mx-auto px-6 py-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}