'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import { Bell, Search, Sun, Moon, Menu, User, LogOut, Settings } from 'lucide-react'
import { useTheme } from 'next-themes'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { useAuthStore } from '@/store/auth'
import { useUIStore } from '@/store/ui'
import { useCallsStore } from '@/store/calls'
import { getInitials } from '@/lib/utils'

export function Header() {
  const router = useRouter()
  const { theme, setTheme } = useTheme()
  const { user, logout } = useAuthStore()
  const { sidebarCollapsed, setMobileMenuOpen, showSuccessToast } = useUIStore()
  const { conversations } = useCallsStore()
  const [searchQuery, setSearchQuery] = React.useState('')

  // Calculate notification count
  const notificationCount = conversations.filter(c => 
    c.status === 'waiting' || c.metadata.humanTakeoverRequested
  ).length

  const handleLogout = async () => {
    try {
      logout()
      showSuccessToast('Successfully logged out')
      router.push('/login')
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`)
    }
  }

  const toggleTheme = () => {
    setTheme(theme === 'dark' ? 'light' : 'dark')
  }

  return (
    <header className={`fixed top-0 right-0 z-30 bg-background border-b border-border transition-all duration-300 ${
      sidebarCollapsed ? 'left-16' : 'left-64'
    }`}>
      <div className="flex items-center justify-between px-6 py-4">
        {/* Mobile Menu Button */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={() => setMobileMenuOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>

        {/* Search Bar */}
        <div className="flex-1 max-w-md mx-4">
          <form onSubmit={handleSearch} className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search calls, conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4"
            />
          </form>
        </div>

        {/* Right Side Actions */}
        <div className="flex items-center space-x-2">
          {/* Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </Button>

          {/* Notifications */}
          <Button
            variant="ghost"
            size="icon"
            className="relative"
            onClick={() => router.push('/conversations?filter=waiting')}
            title="View waiting conversations"
          >
            <Bell className="h-5 w-5" />
            {notificationCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
              >
                {notificationCount > 99 ? '99+' : notificationCount}
              </Badge>
            )}
          </Button>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                <Avatar className="h-10 w-10">
                  <AvatarImage src={user?.avatar} alt={user?.firstName + ' ' + user?.lastName} />
                  <AvatarFallback className="bg-primary text-primary-foreground">
                    {user ? getInitials(`${user.firstName} ${user.lastName}`) : 'U'}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user?.firstName} {user?.lastName}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground">
                    {user?.email}
                  </p>
                  <p className="text-xs leading-none text-muted-foreground capitalize">
                    {user?.role} account
                  </p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              
              <DropdownMenuItem
                onClick={() => router.push('/settings/profile')}
                className="cursor-pointer"
              >
                <User className="mr-2 h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>
              
              <DropdownMenuItem
                onClick={() => router.push('/settings')}
                className="cursor-pointer"
              >
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              
              <DropdownMenuSeparator />
              
              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer text-destructive focus:text-destructive"
              >
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Quick Stats Bar */}
      <div className="border-t border-border bg-muted/30 px-6 py-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center space-x-6">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
              <span>System Online</span>
            </div>
            <div>
              Active Calls: <span className="font-medium text-foreground">
                {conversations.filter(c => c.status === 'active').length}
              </span>
            </div>
            <div>
              Waiting: <span className="font-medium text-foreground">
                {conversations.filter(c => c.status === 'waiting').length}
              </span>
            </div>
          </div>
          <div className="text-xs">
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>
      </div>
    </header>
  )
}