import { io, Socket } from 'socket.io-client'
import { useAuthStore } from '@/store/auth'
import { useCallsStore } from '@/store/calls'
import { useUIStore } from '@/store/ui'

class SocketManager {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false

  constructor() {
    // Auto-connect when user is authenticated
    useAuthStore.subscribe(
      (state) => state.isAuthenticated,
      (isAuthenticated) => {
        if (isAuthenticated) {
          this.connect()
        } else {
          this.disconnect()
        }
      }
    )
  }

  connect(): void {
    if (this.socket?.connected || this.isConnecting) {
      return
    }

    const { tokens, user } = useAuthStore.getState()
    if (!tokens?.accessToken || !user) {
      console.warn('Cannot connect socket: No authentication token')
      return
    }

    this.isConnecting = true

    try {
      this.socket = io(process.env.NEXT_PUBLIC_SOCKET_URL || 'http://localhost:3105', {
        auth: {
          token: tokens.accessToken,
          tenantId: user.tenantId,
          userId: user.id
        },
        transports: ['websocket', 'polling'],
        timeout: 10000,
        reconnection: true,
        reconnectionAttempts: this.maxReconnectAttempts,
        reconnectionDelay: this.reconnectDelay
      })

      this.setupEventHandlers()
      this.isConnecting = false
    } catch (error) {
      console.error('Failed to create socket connection:', error)
      this.isConnecting = false
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.reconnectAttempts = 0
    this.isConnecting = false
  }

  private setupEventHandlers(): void {
    if (!this.socket) return

    // Connection events
    this.socket.on('connect', () => {
      console.log('Socket connected:', this.socket?.id)
      this.reconnectAttempts = 0
      
      useUIStore.getState().showSuccessToast('Connected to real-time updates')
    })

    this.socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason)
      
      if (reason === 'io server disconnect') {
        // Server disconnected the client, manual reconnection needed
        useUIStore.getState().showWarningToast('Connection lost. Attempting to reconnect...')
        setTimeout(() => this.connect(), this.reconnectDelay)
      }
    })

    this.socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error)
      this.reconnectAttempts++
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        useUIStore.getState().showErrorToast('Failed to connect to real-time updates')
      }
    })

    this.socket.on('reconnect', (attemptNumber) => {
      console.log('Socket reconnected after', attemptNumber, 'attempts')
      useUIStore.getState().showSuccessToast('Reconnected to real-time updates')
    })

    this.socket.on('reconnect_error', (error) => {
      console.error('Socket reconnection error:', error)
    })

    this.socket.on('reconnect_failed', () => {
      console.error('Socket reconnection failed after max attempts')
      useUIStore.getState().showErrorToast('Failed to reconnect to real-time updates')
    })

    // Authentication events
    this.socket.on('authenticated', (data) => {
      console.log('Socket authenticated for tenant:', data.tenantId)
    })

    this.socket.on('authentication_error', (error) => {
      console.error('Socket authentication error:', error)
      useUIStore.getState().showErrorToast('Authentication failed for real-time updates')
      
      // Try to refresh token and reconnect
      useAuthStore.getState().refreshToken().then(() => {
        this.disconnect()
        this.connect()
      }).catch(() => {
        useAuthStore.getState().logout()
      })
    })

    // Call events
    this.socket.on('call:created', (data) => {
      console.log('New call created:', data.call)
      useCallsStore.getState().updateCallRealTime(data.call)
      useUIStore.getState().showInfoToast(
        `New ${data.call.direction} call from ${data.call.fromNumber}`,
        'New Call'
      )
    })

    this.socket.on('call:updated', (data) => {
      console.log('Call updated:', data.call)
      useCallsStore.getState().updateCallRealTime(data.call)
      
      if (data.call.status === 'completed') {
        const duration = data.call.duration || 0
        useUIStore.getState().showInfoToast(
          `Call ended after ${Math.floor(duration / 60)}:${(duration % 60).toString().padStart(2, '0')}`,
          'Call Completed'
        )
      }
    })

    this.socket.on('call:ended', (data) => {
      console.log('Call ended:', data.call)
      useCallsStore.getState().updateCallRealTime(data.call)
    })

    // Conversation events
    this.socket.on('conversation:created', (data) => {
      console.log('New conversation created:', data.conversation)
      useCallsStore.getState().updateConversationRealTime(data.conversation)
      useUIStore.getState().showInfoToast(
        'New conversation started',
        'New Conversation'
      )
    })

    this.socket.on('conversation:updated', (data) => {
      console.log('Conversation updated:', data.conversation)
      useCallsStore.getState().updateConversationRealTime(data.conversation)
    })

    this.socket.on('conversation:message', (data) => {
      console.log('New conversation message:', data)
      
      // Refresh the specific conversation to get the new message
      useCallsStore.getState().fetchConversation(data.conversationId)
      
      if (data.message.sender === 'caller') {
        useUIStore.getState().showInfoToast(
          `New message in conversation`,
          'New Message'
        )
      }
    })

    this.socket.on('conversation:takeover_requested', (data) => {
      console.log('Takeover requested for conversation:', data.conversationId)
      useUIStore.getState().showWarningToast(
        'Manual takeover requested for conversation',
        'Takeover Request'
      )
    })

    this.socket.on('conversation:human_joined', (data) => {
      console.log('Human agent joined conversation:', data)
      useUIStore.getState().showSuccessToast(
        'Human agent has joined the conversation',
        'Agent Joined'
      )
    })

    // System events
    this.socket.on('system:notification', (data) => {
      console.log('System notification:', data)
      
      const { type, title, message } = data
      
      switch (type) {
        case 'info':
          useUIStore.getState().showInfoToast(message, title)
          break
        case 'warning':
          useUIStore.getState().showWarningToast(message, title)
          break
        case 'error':
          useUIStore.getState().showErrorToast(message, title)
          break
        case 'success':
          useUIStore.getState().showSuccessToast(message, title)
          break
      }
    })

    this.socket.on('system:maintenance', (data) => {
      console.log('System maintenance notification:', data)
      useUIStore.getState().showWarningToast(
        data.message,
        'System Maintenance'
      )
    })

    this.socket.on('system:update', (data) => {
      console.log('System update notification:', data)
      if (data.requiresReload) {
        useUIStore.getState().showInfoToast(
          'A system update is available. Please refresh the page.',
          'System Update'
        )
      }
    })

    // Phone number events
    this.socket.on('phone:provisioned', (data) => {
      console.log('Phone number provisioned:', data)
      useUIStore.getState().showSuccessToast(
        `Phone number ${data.number} has been provisioned`,
        'Number Provisioned'
      )
    })

    this.socket.on('phone:status_changed', (data) => {
      console.log('Phone number status changed:', data)
    })

    // Error handling
    this.socket.on('error', (error) => {
      console.error('Socket error:', error)
      useUIStore.getState().showErrorToast(
        'Real-time connection error occurred',
        'Connection Error'
      )
    })
  }

  // Public methods for sending events
  emit(event: string, data?: any): void {
    if (this.socket?.connected) {
      this.socket.emit(event, data)
    } else {
      console.warn('Socket not connected, cannot emit event:', event)
    }
  }

  // Join specific rooms
  joinCallRoom(callId: string): void {
    this.emit('join:call', { callId })
  }

  leaveCallRoom(callId: string): void {
    this.emit('leave:call', { callId })
  }

  joinConversationRoom(conversationId: string): void {
    this.emit('join:conversation', { conversationId })
  }

  leaveConversationRoom(conversationId: string): void {
    this.emit('leave:conversation', { conversationId })
  }

  // Check connection status
  isConnected(): boolean {
    return this.socket?.connected || false
  }

  // Get socket ID
  getSocketId(): string | undefined {
    return this.socket?.id
  }
}

// Create singleton instance
export const socketManager = new SocketManager()

// Hooks for React components
export function useSocket() {
  return socketManager
}

export function useSocketEvent(event: string, handler: (data: any) => void) {
  const socket = socketManager
  
  // Note: This would need React.useEffect for actual implementation
  // For now, this is a placeholder - implement useEffect when needed
  console.log('Socket event listener would be set up for:', event)
}

// Auto-connect when the module loads (if user is already authenticated)
if (typeof window !== 'undefined' && useAuthStore.getState().isAuthenticated) {
  socketManager.connect()
}