'use client'

import React from 'react'
import { useCallsStore } from '@/store/calls'
import { useUIStore } from '@/store/ui'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Phone, 
  PhoneCall, 
  MessageCircle, 
  Clock, 
  TrendingUp, 
  TrendingDown,
  Users,
  Activity,
  RefreshCw,
  ArrowUpRight,
  ArrowDownLeft,
  UserCheck
} from 'lucide-react'
import { formatDuration, formatRelativeTime, getStatusColor } from '@/lib/utils'
import Link from 'next/link'

export default function DashboardPage() {
  const { 
    dashboardStats, 
    calls, 
    conversations, 
    statsLoading, 
    refreshDashboardStats,
    fetchCalls,
    fetchConversations
  } = useCallsStore()
  const { setBreadcrumbs, setCurrentPage } = useUIStore()

  React.useEffect(() => {
    setCurrentPage('Dashboard')
    setBreadcrumbs([{ label: 'Dashboard' }])
  }, [setCurrentPage, setBreadcrumbs])

  const handleRefresh = async () => {
    await Promise.all([
      refreshDashboardStats(),
      fetchCalls({ limit: 5 }),
      fetchConversations({ limit: 5 })
    ])
  }

  // Calculate some derived stats
  const recentCalls = calls.slice(0, 5)
  const activeConversations = conversations.filter(c => c.status === 'active' || c.status === 'waiting')
  const completedToday = calls.filter(c => {
    const today = new Date()
    const callDate = new Date(c.createdAt)
    return callDate.toDateString() === today.toDateString() && c.status === 'completed'
  }).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back! Here's what's happening with your calls today.
          </p>
        </div>
        <Button onClick={handleRefresh} disabled={statsLoading} variant="outline">
          <RefreshCw className={`mr-2 h-4 w-4 ${statsLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Calls</CardTitle>
            <Phone className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">
              {dashboardStats?.calls.active || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Currently in progress
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Calls Today</CardTitle>
            <PhoneCall className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {completedToday}
            </div>
            <p className="text-xs text-muted-foreground">
              {dashboardStats?.calls.missed || 0} missed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Conversations</CardTitle>
            <MessageCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">
              {activeConversations.length}
            </div>
            <p className="text-xs text-muted-foreground">
              Needs attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Call Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardStats ? formatDuration(dashboardStats.calls.averageDuration) : '0s'}
            </div>
            <p className="text-xs text-muted-foreground">
              This week
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts and Activity */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Call Volume Chart */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Call Activity
            </CardTitle>
            <CardDescription>
              Real-time overview of your call volume
            </CardDescription>
          </CardHeader>
          <CardContent className="pl-2">
            {/* Placeholder for chart - you can integrate recharts here */}
            <div className="h-[200px] flex items-center justify-center border border-dashed border-muted-foreground/20 rounded-lg">
              <div className="text-center text-muted-foreground">
                <TrendingUp className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Call volume chart</p>
                <p className="text-sm">Real-time data visualization</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Recent Activity
            </CardTitle>
            <CardDescription>
              Latest calls and conversations
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentCalls.length > 0 ? (
                recentCalls.map((call) => (
                  <div key={call.id} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {call.direction === 'inbound' ? (
                        <ArrowDownLeft className="h-4 w-4 text-success" />
                      ) : (
                        <ArrowUpRight className="h-4 w-4 text-primary" />
                      )}
                      <div>
                        <p className="text-sm font-medium">
                          {call.fromNumber}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatRelativeTime(call.startTime)}
                        </p>
                      </div>
                    </div>
                    <Badge 
                      variant="outline" 
                      className={getStatusColor(call.status)}
                    >
                      {call.status}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  <Phone className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No recent calls</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions and Conversations */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Active Conversations */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Active Conversations</CardTitle>
              <CardDescription>
                Conversations requiring attention
              </CardDescription>
            </div>
            <Button variant="outline" asChild>
              <Link href="/conversations">
                View All
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {activeConversations.length > 0 ? (
                activeConversations.slice(0, 3).map((conversation) => (
                  <div key={conversation.id} className="flex items-center justify-between p-3 border rounded-lg">
                    <div className="flex items-center space-x-3">
                      <div className={`w-2 h-2 rounded-full ${
                        conversation.status === 'active' ? 'bg-success animate-pulse' : 'bg-warning'
                      }`} />
                      <div>
                        <p className="text-sm font-medium">
                          {conversation.subject || 'New Conversation'}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatRelativeTime(conversation.startTime)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className={getStatusColor(conversation.status)}>
                        {conversation.status}
                      </Badge>
                      {conversation.metadata.humanTakeoverRequested && (
                        <Badge variant="destructive" className="text-xs">
                          Takeover
                        </Badge>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No active conversations</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
            <CardDescription>
              Current system health and metrics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
                  <span className="text-sm font-medium">Call Service</span>
                </div>
                <Badge variant="outline" className="text-success bg-success/10 border-success/20">
                  Online
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
                  <span className="text-sm font-medium">AI Assistant</span>
                </div>
                <Badge variant="outline" className="text-success bg-success/10 border-success/20">
                  Active
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
                  <span className="text-sm font-medium">Phone Numbers</span>
                </div>
                <Badge variant="outline">
                  {dashboardStats?.phoneNumbers.active || 0} Active
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <UserCheck className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">Response Rate</span>
                </div>
                <Badge variant="outline" className="text-success bg-success/10 border-success/20">
                  {dashboardStats ? Math.round(dashboardStats.calls.conversionRate * 100) : 0}%
                </Badge>
              </div>

              <div className="pt-2 border-t">
                <div className="text-xs text-muted-foreground text-center">
                  Last updated: {formatRelativeTime(new Date())}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}