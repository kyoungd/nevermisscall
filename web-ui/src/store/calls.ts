import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { Call, Conversation, CallFilters, ConversationFilters, DashboardStats } from '@/types/calls'
import { PaginatedRequest, PaginationMeta } from '@/types/api'
import { apiClient } from '@/lib/api-client'

interface CallsState {
  // Calls
  calls: Call[]
  callsLoading: boolean
  callsError: string | null
  callsPagination: PaginationMeta | null
  activeCall: Call | null
  
  // Conversations
  conversations: Conversation[]
  conversationsLoading: boolean
  conversationsError: string | null
  conversationsPagination: PaginationMeta | null
  activeConversation: Conversation | null
  
  // Dashboard stats
  dashboardStats: DashboardStats | null
  statsLoading: boolean
  statsError: string | null
  
  // Filters
  callFilters: CallFilters
  conversationFilters: ConversationFilters
  
  // Real-time updates
  realTimeEnabled: boolean
}

interface CallsActions {
  // Calls
  fetchCalls: (params?: PaginatedRequest & CallFilters) => Promise<void>
  fetchCall: (id: string) => Promise<Call | null>
  refreshCalls: () => Promise<void>
  setCallFilters: (filters: Partial<CallFilters>) => void
  clearCallFilters: () => void
  setActiveCall: (call: Call | null) => void
  
  // Conversations
  fetchConversations: (params?: PaginatedRequest & ConversationFilters) => Promise<void>
  fetchConversation: (id: string) => Promise<Conversation | null>
  refreshConversations: () => Promise<void>
  setConversationFilters: (filters: Partial<ConversationFilters>) => void
  clearConversationFilters: () => void
  setActiveConversation: (conversation: Conversation | null) => void
  requestManualTakeover: (conversationId: string) => Promise<void>
  updateConversationStatus: (conversationId: string, status: string) => Promise<void>
  addConversationNote: (conversationId: string, note: string) => Promise<void>
  
  // Dashboard
  fetchDashboardStats: () => Promise<void>
  refreshDashboardStats: () => Promise<void>
  
  // Real-time
  updateCallRealTime: (call: Call) => void
  updateConversationRealTime: (conversation: Conversation) => void
  setRealTimeEnabled: (enabled: boolean) => void
  
  // Error handling
  clearErrors: () => void
}

export const useCallsStore = create<CallsState & CallsActions>()(
  subscribeWithSelector((set, get) => ({
    // State
    calls: [],
    callsLoading: false,
    callsError: null,
    callsPagination: null,
    activeCall: null,
    
    conversations: [],
    conversationsLoading: false,
    conversationsError: null,
    conversationsPagination: null,
    activeConversation: null,
    
    dashboardStats: null,
    statsLoading: false,
    statsError: null,
    
    callFilters: {},
    conversationFilters: {},
    
    realTimeEnabled: true,

    // Actions
    fetchCalls: async (params) => {
      try {
        set({ callsLoading: true, callsError: null })
        
        const response = await apiClient.get('/calls', { params })
        
        if (response.data.success) {
          set({
            calls: response.data.data || [],
            callsPagination: response.data.meta?.pagination || null,
            callsLoading: false
          })
        } else {
          throw new Error(response.data.error?.message || 'Failed to fetch calls')
        }
      } catch (error: any) {
        set({
          callsError: error.response?.data?.error?.message || error.message,
          callsLoading: false
        })
      }
    },

    fetchCall: async (id: string) => {
      try {
        const response = await apiClient.get(`/calls/${id}`)
        
        if (response.data.success && response.data.data) {
          const call = response.data.data
          
          // Update call in list if it exists
          const { calls } = get()
          const updatedCalls = calls.map(c => c.id === id ? call : c)
          set({ calls: updatedCalls })
          
          return call
        } else {
          throw new Error(response.data.error?.message || 'Failed to fetch call')
        }
      } catch (error: any) {
        console.error('Failed to fetch call:', error)
        return null
      }
    },

    refreshCalls: async () => {
      const { callFilters } = get()
      await get().fetchCalls(callFilters)
    },

    setCallFilters: (filters: Partial<CallFilters>) => {
      set({ callFilters: { ...get().callFilters, ...filters } })
    },

    clearCallFilters: () => {
      set({ callFilters: {} })
    },

    setActiveCall: (call: Call | null) => {
      set({ activeCall: call })
    },

    fetchConversations: async (params) => {
      try {
        set({ conversationsLoading: true, conversationsError: null })
        
        const response = await apiClient.get('/conversations', { params })
        
        if (response.data.success) {
          set({
            conversations: response.data.data || [],
            conversationsPagination: response.data.meta?.pagination || null,
            conversationsLoading: false
          })
        } else {
          throw new Error(response.data.error?.message || 'Failed to fetch conversations')
        }
      } catch (error: any) {
        set({
          conversationsError: error.response?.data?.error?.message || error.message,
          conversationsLoading: false
        })
      }
    },

    fetchConversation: async (id: string) => {
      try {
        const response = await apiClient.get(`/conversations/${id}`)
        
        if (response.data.success && response.data.data) {
          const conversation = response.data.data
          
          // Update conversation in list if it exists
          const { conversations } = get()
          const updatedConversations = conversations.map(c => c.id === id ? conversation : c)
          set({ conversations: updatedConversations })
          
          return conversation
        } else {
          throw new Error(response.data.error?.message || 'Failed to fetch conversation')
        }
      } catch (error: any) {
        console.error('Failed to fetch conversation:', error)
        return null
      }
    },

    refreshConversations: async () => {
      const { conversationFilters } = get()
      await get().fetchConversations(conversationFilters)
    },

    setConversationFilters: (filters: Partial<ConversationFilters>) => {
      set({ conversationFilters: { ...get().conversationFilters, ...filters } })
    },

    clearConversationFilters: () => {
      set({ conversationFilters: {} })
    },

    setActiveConversation: (conversation: Conversation | null) => {
      set({ activeConversation: conversation })
    },

    requestManualTakeover: async (conversationId: string) => {
      try {
        const response = await apiClient.post(`/conversations/${conversationId}/takeover`)
        
        if (response.data.success) {
          // Update conversation with takeover status
          const { conversations } = get()
          const updatedConversations = conversations.map(c => 
            c.id === conversationId 
              ? { ...c, metadata: { ...c.metadata, humanTakeoverRequested: true, humanTakeoverAt: new Date() } }
              : c
          )
          set({ conversations: updatedConversations })
        } else {
          throw new Error(response.data.error?.message || 'Failed to request takeover')
        }
      } catch (error: any) {
        throw error
      }
    },

    updateConversationStatus: async (conversationId: string, status: string) => {
      try {
        const response = await apiClient.patch(`/conversations/${conversationId}`, { status })
        
        if (response.data.success) {
          const { conversations } = get()
          const updatedConversations = conversations.map(c => 
            c.id === conversationId ? { ...c, status } : c
          )
          set({ conversations: updatedConversations })
        } else {
          throw new Error(response.data.error?.message || 'Failed to update conversation')
        }
      } catch (error: any) {
        throw error
      }
    },

    addConversationNote: async (conversationId: string, note: string) => {
      try {
        const response = await apiClient.post(`/conversations/${conversationId}/notes`, { note })
        
        if (response.data.success && response.data.data) {
          // Refresh conversation to get updated data
          await get().fetchConversation(conversationId)
        } else {
          throw new Error(response.data.error?.message || 'Failed to add note')
        }
      } catch (error: any) {
        throw error
      }
    },

    fetchDashboardStats: async () => {
      try {
        set({ statsLoading: true, statsError: null })
        
        const response = await apiClient.get('/dashboard/stats')
        
        if (response.data.success) {
          set({
            dashboardStats: response.data.data,
            statsLoading: false
          })
        } else {
          throw new Error(response.data.error?.message || 'Failed to fetch dashboard stats')
        }
      } catch (error: any) {
        set({
          statsError: error.response?.data?.error?.message || error.message,
          statsLoading: false
        })
      }
    },

    refreshDashboardStats: async () => {
      await get().fetchDashboardStats()
    },

    updateCallRealTime: (call: Call) => {
      const { realTimeEnabled, calls } = get()
      if (!realTimeEnabled) return
      
      const updatedCalls = calls.some(c => c.id === call.id)
        ? calls.map(c => c.id === call.id ? call : c)
        : [call, ...calls]
      
      set({ calls: updatedCalls })
      
      // Update active call if it matches
      const { activeCall } = get()
      if (activeCall?.id === call.id) {
        set({ activeCall: call })
      }
    },

    updateConversationRealTime: (conversation: Conversation) => {
      const { realTimeEnabled, conversations } = get()
      if (!realTimeEnabled) return
      
      const updatedConversations = conversations.some(c => c.id === conversation.id)
        ? conversations.map(c => c.id === conversation.id ? conversation : c)
        : [conversation, ...conversations]
      
      set({ conversations: updatedConversations })
      
      // Update active conversation if it matches
      const { activeConversation } = get()
      if (activeConversation?.id === conversation.id) {
        set({ activeConversation: conversation })
      }
    },

    setRealTimeEnabled: (enabled: boolean) => {
      set({ realTimeEnabled: enabled })
    },

    clearErrors: () => {
      set({
        callsError: null,
        conversationsError: null,
        statsError: null
      })
    }
  }))
)