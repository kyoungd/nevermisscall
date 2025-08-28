'use client'

import React from 'react'
import { useCallsStore } from '@/store/calls'
import { useUIStore } from '@/store/ui'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { 
  Phone, 
  Search,
  Filter,
  Download,
  Play,
  ArrowUpRight,
  ArrowDownLeft,
  Clock,
  Calendar,
  MoreVertical,
  RefreshCw
} from 'lucide-react'
import { formatDuration, formatRelativeTime, formatPhoneNumber, getStatusColor } from '@/lib/utils'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export default function CallsPage() {
  const { 
    calls, 
    callsLoading, 
    callFilters,
    setCallFilters,
    fetchCalls,
    refreshCalls
  } = useCallsStore()
  const { setBreadcrumbs, setCurrentPage } = useUIStore()
  
  const [searchQuery, setSearchQuery] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const [directionFilter, setDirectionFilter] = React.useState<string>('all')

  React.useEffect(() => {
    setCurrentPage('Calls')
    setBreadcrumbs([{ label: 'Calls' }])
  }, [setCurrentPage, setBreadcrumbs])

  // Handle search
  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setCallFilters({ 
      ...callFilters, 
      phoneNumber: query.trim() || undefined 
    })
  }

  // Handle filters
  const handleStatusFilter = (status: string) => {
    setStatusFilter(status)
    setCallFilters({
      ...callFilters,
      status: status === 'all' ? undefined : [status as any]
    })
  }

  const handleDirectionFilter = (direction: string) => {
    setDirectionFilter(direction)
    setCallFilters({
      ...callFilters,
      direction: direction === 'all' ? undefined : [direction as any]
    })
  }

  // Load calls when filters change
  React.useEffect(() => {
    fetchCalls({ ...callFilters, limit: 50 })
  }, [callFilters, fetchCalls])

  const handlePlayRecording = (callId: string) => {
    // Implement recording playback
    console.log('Play recording for call:', callId)
  }

  const handleExportCalls = () => {
    // Implement call export
    console.log('Export calls')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Calls</h1>
          <p className="text-muted-foreground">
            Monitor and manage all your call activity
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={handleExportCalls} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          <Button onClick={refreshCalls} disabled={callsLoading} variant="outline">
            <RefreshCw className={`mr-2 h-4 w-4 ${callsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Filters</CardTitle>
          <CardDescription>
            Search and filter your call history
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col space-y-4 sm:flex-row sm:space-y-0 sm:space-x-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by phone number..."
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={handleStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="missed">Missed</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>

            {/* Direction Filter */}
            <Select value={directionFilter} onValueChange={handleDirectionFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Directions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Directions</SelectItem>
                <SelectItem value="inbound">Inbound</SelectItem>
                <SelectItem value="outbound">Outbound</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Calls List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Call History
          </CardTitle>
          <CardDescription>
            {calls.length} calls found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {callsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <span className="ml-2 text-muted-foreground">Loading calls...</span>
            </div>
          ) : calls.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold">No calls found</h3>
              <p>Try adjusting your filters or search criteria.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {calls.map((call) => (
                <div
                  key={call.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  {/* Call Info */}
                  <div className="flex items-center space-x-4">
                    {/* Direction Icon */}
                    <div className="flex-shrink-0">
                      {call.direction === 'inbound' ? (
                        <div className="p-2 bg-success/10 rounded-full">
                          <ArrowDownLeft className="h-4 w-4 text-success" />
                        </div>
                      ) : (
                        <div className="p-2 bg-primary/10 rounded-full">
                          <ArrowUpRight className="h-4 w-4 text-primary" />
                        </div>
                      )}
                    </div>

                    {/* Call Details */}
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-medium">
                          {formatPhoneNumber(call.fromNumber)}
                        </h3>
                        {call.direction === 'inbound' && (
                          <ArrowDownLeft className="h-3 w-3 text-muted-foreground" />
                        )}
                        <span className="text-muted-foreground">
                          {formatPhoneNumber(call.toNumber)}
                        </span>
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatRelativeTime(call.startTime)}</span>
                        </div>
                        {call.duration && (
                          <div className="flex items-center space-x-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDuration(call.duration)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Status and Actions */}
                  <div className="flex items-center space-x-3">
                    {/* Status Badge */}
                    <Badge 
                      variant="outline" 
                      className={getStatusColor(call.status)}
                    >
                      {call.status}
                    </Badge>

                    {/* Recording Button */}
                    {call.recordingUrl && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handlePlayRecording(call.id)}
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                    )}

                    {/* More Actions */}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuLabel>Actions</DropdownMenuLabel>
                        <DropdownMenuItem>
                          View Details
                        </DropdownMenuItem>
                        {call.recordingUrl && (
                          <DropdownMenuItem onClick={() => handlePlayRecording(call.id)}>
                            Play Recording
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem>
                          Call Back
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem>
                          Export Call Data
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}