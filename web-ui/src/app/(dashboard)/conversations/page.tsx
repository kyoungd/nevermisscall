'use client'

import React from 'react'
import { useCallsStore } from '@/store/calls'
import { useUIStore } from '@/store/ui'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { 
  MessageCircle,
  Search,
  Filter,
  UserCheck,
  Clock,
  AlertTriangle,
  Bot,
  User,
  MoreVertical,
  RefreshCw,
  Plus,
  Tag
} from 'lucide-react'
import { formatRelativeTime, getStatusColor, getInitials } from '@/lib/utils'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Textarea } from '@/components/ui/textarea'

export default function ConversationsPage() {
  const { 
    conversations, 
    conversationsLoading,
    conversationFilters,
    setConversationFilters,
    fetchConversations,
    refreshConversations,
    requestManualTakeover,
    updateConversationStatus,
    addConversationNote
  } = useCallsStore()
  const { setBreadcrumbs, setCurrentPage, showSuccessToast, showErrorToast } = useUIStore()
  
  const [searchQuery, setSearchQuery] = React.useState('')
  const [statusFilter, setStatusFilter] = React.useState<string>('all')
  const [priorityFilter, setPriorityFilter] = React.useState<string>('all')
  const [selectedConversation, setSelectedConversation] = React.useState<string | null>(null)
  const [note, setNote] = React.useState('')

  React.useEffect(() => {
    setCurrentPage('Conversations')
    setBreadcrumbs([{ label: 'Conversations' }])
  }, [setCurrentPage, setBreadcrumbs])

  // Handle search and filters
  React.useEffect(() => {
    const filters: any = {}
    
    if (statusFilter !== 'all') {
      filters.status = [statusFilter]
    }
    
    if (priorityFilter !== 'all') {
      filters.priority = [priorityFilter]
    }

    setConversationFilters(filters)
    fetchConversations({ ...filters, limit: 50 })
  }, [statusFilter, priorityFilter, setConversationFilters, fetchConversations])

  const handleTakeover = async (conversationId: string) => {
    try {
      await requestManualTakeover(conversationId)
      showSuccessToast('Takeover request sent successfully')
    } catch (error: any) {
      showErrorToast(error.message || 'Failed to request takeover')
    }
  }

  const handleStatusChange = async (conversationId: string, newStatus: string) => {
    try {
      await updateConversationStatus(conversationId, newStatus)
      showSuccessToast('Status updated successfully')
    } catch (error: any) {
      showErrorToast(error.message || 'Failed to update status')
    }
  }

  const handleAddNote = async () => {
    if (!selectedConversation || !note.trim()) return

    try {
      await addConversationNote(selectedConversation, note.trim())
      setNote('')
      setSelectedConversation(null)
      showSuccessToast('Note added successfully')
    } catch (error: any) {
      showErrorToast(error.message || 'Failed to add note')
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-destructive bg-destructive/10 border-destructive/20'
      case 'high':
        return 'text-warning bg-warning/10 border-warning/20'
      case 'normal':
        return 'text-muted-foreground bg-muted border-border'
      case 'low':
        return 'text-muted-foreground bg-muted/50 border-border'
      default:
        return 'text-muted-foreground bg-muted border-border'
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Conversations</h1>
          <p className="text-muted-foreground">
            Monitor and manage customer conversations
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={refreshConversations} disabled={conversationsLoading} variant="outline">
            <RefreshCw className={`mr-2 h-4 w-4 ${conversationsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <MessageCircle className="h-4 w-4 text-muted-foreground" />
              <div className="ml-2">
                <p className="text-2xl font-bold text-success">
                  {conversations.filter(c => c.status === 'active').length}
                </p>
                <p className="text-xs text-muted-foreground">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <div className="ml-2">
                <p className="text-2xl font-bold text-warning">
                  {conversations.filter(c => c.status === 'waiting').length}
                </p>
                <p className="text-xs text-muted-foreground">Waiting</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              <div className="ml-2">
                <p className="text-2xl font-bold text-destructive">
                  {conversations.filter(c => c.metadata.humanTakeoverRequested).length}
                </p>
                <p className="text-xs text-muted-foreground">Takeover Requests</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center">
              <Bot className="h-4 w-4 text-muted-foreground" />
              <div className="ml-2">
                <p className="text-2xl font-bold">
                  {conversations.filter(c => c.metadata.aiHandled).length}
                </p>
                <p className="text-xs text-muted-foreground">AI Handled</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col space-y-4 sm:flex-row sm:space-y-0 sm:space-x-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Status Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="waiting">Waiting</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="closed">Closed</SelectItem>
              </SelectContent>
            </Select>

            {/* Priority Filter */}
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Conversations List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5" />
            Conversations
          </CardTitle>
          <CardDescription>
            {conversations.length} conversations found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {conversationsLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
              <span className="ml-2 text-muted-foreground">Loading conversations...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-semibold">No conversations found</h3>
              <p>Try adjusting your filters or search criteria.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  {/* Conversation Info */}
                  <div className="flex items-center space-x-4">
                    {/* Avatar/Status */}
                    <div className="relative">
                      <Avatar className="h-10 w-10">
                        <AvatarFallback className={`${conversation.metadata.aiHandled ? 'bg-primary/10 text-primary' : 'bg-success/10 text-success'}`}>
                          {conversation.metadata.aiHandled ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                        </AvatarFallback>
                      </Avatar>
                      <div className={`absolute -bottom-1 -right-1 w-3 h-3 rounded-full border-2 border-background ${
                        conversation.status === 'active' ? 'bg-success animate-pulse' : 
                        conversation.status === 'waiting' ? 'bg-warning' : 'bg-muted-foreground'
                      }`} />
                    </div>

                    {/* Details */}
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <h3 className="font-medium">
                          {conversation.subject || 'New Conversation'}
                        </h3>
                        <Badge 
                          variant="outline" 
                          className={getPriorityColor(conversation.priority)}
                        >
                          {conversation.priority}
                        </Badge>
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <span>{formatRelativeTime(conversation.startTime)}</span>
                        <span>{conversation.messages.length} messages</span>
                        {conversation.metadata.appointmentScheduled && (
                          <Badge variant="outline" className="text-xs">
                            Appointment Scheduled
                          </Badge>
                        )}
                      </div>
                      {conversation.tags.length > 0 && (
                        <div className="flex items-center space-x-1">
                          <Tag className="h-3 w-3 text-muted-foreground" />
                          <div className="flex space-x-1">
                            {conversation.tags.slice(0, 3).map((tag, index) => (
                              <Badge key={index} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                            {conversation.tags.length > 3 && (
                              <Badge variant="outline" className="text-xs">
                                +{conversation.tags.length - 3}
                              </Badge>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Status and Actions */}
                  <div className="flex items-center space-x-3">
                    {/* Status Badge */}
                    <Badge 
                      variant="outline" 
                      className={getStatusColor(conversation.status)}
                    >
                      {conversation.status}
                    </Badge>

                    {/* Takeover Request Indicator */}
                    {conversation.metadata.humanTakeoverRequested && (
                      <Badge variant="destructive" className="text-xs">
                        Takeover Requested
                      </Badge>
                    )}

                    {/* Quick Actions */}
                    {conversation.status === 'active' || conversation.status === 'waiting' ? (
                      <Button
                        size="sm"
                        variant={conversation.metadata.humanTakeoverRequested ? 'destructive' : 'outline'}
                        onClick={() => handleTakeover(conversation.id)}
                        disabled={conversation.metadata.humanTakeoverRequested}
                      >
                        <UserCheck className="h-4 w-4 mr-1" />
                        {conversation.metadata.humanTakeoverRequested ? 'Requested' : 'Take Over'}
                      </Button>
                    ) : null}

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
                          View Messages
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem 
                          onClick={() => handleStatusChange(conversation.id, 'resolved')}
                        >
                          Mark Resolved
                        </DropdownMenuItem>
                        <DropdownMenuItem 
                          onClick={() => handleStatusChange(conversation.id, 'closed')}
                        >
                          Close Conversation
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <Dialog>
                          <DialogTrigger asChild>
                            <DropdownMenuItem 
                              onSelect={(e) => {
                                e.preventDefault()
                                setSelectedConversation(conversation.id)
                              }}
                            >
                              Add Note
                            </DropdownMenuItem>
                          </DialogTrigger>
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Add Note</DialogTitle>
                              <DialogDescription>
                                Add a note to this conversation for future reference.
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4">
                              <Textarea
                                placeholder="Enter your note here..."
                                value={note}
                                onChange={(e) => setNote(e.target.value)}
                                rows={4}
                              />
                              <div className="flex justify-end space-x-2">
                                <Button
                                  variant="outline"
                                  onClick={() => {
                                    setNote('')
                                    setSelectedConversation(null)
                                  }}
                                >
                                  Cancel
                                </Button>
                                <Button onClick={handleAddNote} disabled={!note.trim()}>
                                  Add Note
                                </Button>
                              </div>
                            </div>
                          </DialogContent>
                        </Dialog>
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