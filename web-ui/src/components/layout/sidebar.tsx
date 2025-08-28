'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store/ui'
import { useCallsStore } from '@/store/calls'
import { useSocketContext } from '@/components/providers/socket-provider'
import {
  LayoutDashboard,
  Phone,
  MessageCircle,
  Settings,
  Users,
  PhoneCall,
  TrendingUp,
  Bell,
  ChevronLeft,
  ChevronRight,
  Wifi,
  WifiOff
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface NavItem {
  href: string
  icon: React.ComponentType<{ className?: string }>
  label: string
  badge?: string | number
  active?: boolean
}

export function Sidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()
  const { conversations, dashboardStats } = useCallsStore()
  const { isConnected } = useSocketContext()

  // Calculate active conversations count
  const activeConversations = conversations.filter(c => 
    c.status === 'active' || c.status === 'waiting'
  ).length

  const navItems: NavItem[] = [
    {
      href: '/dashboard',
      icon: LayoutDashboard,
      label: 'Dashboard',
      active: pathname === '/dashboard'
    },
    {
      href: '/calls',
      icon: Phone,
      label: 'Calls',
      badge: dashboardStats?.calls.active || 0,
      active: pathname.startsWith('/calls')
    },
    {
      href: '/conversations',
      icon: MessageCircle,
      label: 'Conversations',
      badge: activeConversations > 0 ? activeConversations : undefined,
      active: pathname.startsWith('/conversations')
    },
    {
      href: '/phone-numbers',
      icon: PhoneCall,
      label: 'Phone Numbers',
      active: pathname.startsWith('/phone-numbers')
    },
    {
      href: '/analytics',
      icon: TrendingUp,
      label: 'Analytics',
      active: pathname.startsWith('/analytics')
    },
    {
      href: '/users',
      icon: Users,
      label: 'Users',
      active: pathname.startsWith('/users')
    },
    {
      href: '/settings',
      icon: Settings,
      label: 'Settings',
      active: pathname.startsWith('/settings')
    }
  ]

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 z-40 h-screen bg-card border-r border-border transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        {!sidebarCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Phone className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-lg">NeverMissCall</span>
          </div>
        )}
        
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleSidebar}
          className="h-8 w-8"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Connection Status */}
      <div className={cn(
        'px-4 py-2 border-b border-border',
        sidebarCollapsed && 'px-2'
      )}>
        <div className={cn(
          'flex items-center space-x-2 text-sm',
          sidebarCollapsed && 'justify-center'
        )}>
          {isConnected ? (
            <>
              <Wifi className="h-4 w-4 text-success" />
              {!sidebarCollapsed && <span className="text-success">Connected</span>}
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-destructive" />
              {!sidebarCollapsed && <span className="text-destructive">Disconnected</span>}
            </>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="p-2 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                'hover:bg-accent hover:text-accent-foreground',
                item.active && 'bg-primary text-primary-foreground hover:bg-primary/90',
                sidebarCollapsed && 'justify-center px-2'
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              
              {!sidebarCollapsed && (
                <>
                  <span className="flex-1">{item.label}</span>
                  {item.badge && (
                    <Badge 
                      variant={item.active ? 'secondary' : 'default'}
                      className="h-5 px-2 text-xs"
                    >
                      {item.badge}
                    </Badge>
                  )}
                </>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Quick Actions */}
      {!sidebarCollapsed && (
        <div className="absolute bottom-4 left-4 right-4">
          <div className="space-y-2">
            <Button
              variant="outline"
              size="sm"
              className="w-full justify-start"
              asChild
            >
              <Link href="/conversations?filter=waiting">
                <Bell className="h-4 w-4 mr-2" />
                Waiting Conversations
                {activeConversations > 0 && (
                  <Badge variant="destructive" className="ml-auto h-5 px-2 text-xs">
                    {activeConversations}
                  </Badge>
                )}
              </Link>
            </Button>
          </div>
        </div>
      )}
    </aside>
  )
}