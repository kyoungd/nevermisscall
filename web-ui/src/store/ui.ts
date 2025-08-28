import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { Toast, Modal, UIPreferences } from '@/types'

interface UIState {
  // Navigation and layout
  sidebarCollapsed: boolean
  mobileMenuOpen: boolean
  
  // Theme and preferences
  theme: 'light' | 'dark' | 'system'
  preferences: UIPreferences
  
  // Notifications and toasts
  toasts: Toast[]
  
  // Modals and dialogs
  modals: Modal[]
  
  // Loading states
  globalLoading: boolean
  loadingText: string | null
  
  // Page state
  currentPage: string
  breadcrumbs: Array<{ label: string; href?: string }>
}

interface UIActions {
  // Navigation and layout
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setMobileMenuOpen: (open: boolean) => void
  
  // Theme and preferences
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  updatePreferences: (preferences: Partial<UIPreferences>) => void
  
  // Notifications and toasts
  addToast: (toast: Omit<Toast, 'id'>) => void
  removeToast: (id: string) => void
  clearToasts: () => void
  
  // Modals and dialogs
  openModal: (modal: Omit<Modal, 'id'>) => void
  closeModal: (id: string) => void
  closeAllModals: () => void
  
  // Loading states
  setGlobalLoading: (loading: boolean, text?: string) => void
  
  // Page state
  setCurrentPage: (page: string) => void
  setBreadcrumbs: (breadcrumbs: Array<{ label: string; href?: string }>) => void
  
  // Utility actions
  showSuccessToast: (message: string, title?: string) => void
  showErrorToast: (message: string, title?: string) => void
  showWarningToast: (message: string, title?: string) => void
  showInfoToast: (message: string, title?: string) => void
}

export const useUIStore = create<UIState & UIActions>()(
  persist(
    (set, get) => ({
      // State
      sidebarCollapsed: false,
      mobileMenuOpen: false,
      
      theme: 'system',
      preferences: {
        theme: 'system',
        sidebarCollapsed: false,
        compactMode: false,
        animations: true,
        autoRefresh: true,
        refreshInterval: 30000
      },
      
      toasts: [],
      modals: [],
      
      globalLoading: false,
      loadingText: null,
      
      currentPage: '',
      breadcrumbs: [],

      // Actions
      toggleSidebar: () => {
        const collapsed = !get().sidebarCollapsed
        set({ sidebarCollapsed: collapsed })
        get().updatePreferences({ sidebarCollapsed: collapsed })
      },

      setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed })
        get().updatePreferences({ sidebarCollapsed: collapsed })
      },

      setMobileMenuOpen: (open: boolean) => {
        set({ mobileMenuOpen: open })
      },

      setTheme: (theme: 'light' | 'dark' | 'system') => {
        set({ theme })
        get().updatePreferences({ theme })
        
        // Apply theme to document
        const root = window.document.documentElement
        
        if (theme === 'system') {
          const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
          root.classList.toggle('dark', systemTheme === 'dark')
        } else {
          root.classList.toggle('dark', theme === 'dark')
        }
      },

      updatePreferences: (newPreferences: Partial<UIPreferences>) => {
        const preferences = { ...get().preferences, ...newPreferences }
        set({ preferences })
      },

      addToast: (toast: Omit<Toast, 'id'>) => {
        const id = Date.now().toString()
        const newToast: Toast = {
          ...toast,
          id,
          duration: toast.duration || 5000
        }
        
        set({ toasts: [...get().toasts, newToast] })
        
        // Auto-remove toast after duration (if not persistent)
        if (!toast.persistent && newToast.duration > 0) {
          setTimeout(() => {
            get().removeToast(id)
          }, newToast.duration)
        }
      },

      removeToast: (id: string) => {
        set({ toasts: get().toasts.filter(toast => toast.id !== id) })
      },

      clearToasts: () => {
        set({ toasts: [] })
      },

      openModal: (modal: Omit<Modal, 'id'>) => {
        const id = Date.now().toString()
        const newModal: Modal = { ...modal, id }
        set({ modals: [...get().modals, newModal] })
      },

      closeModal: (id: string) => {
        const modal = get().modals.find(m => m.id === id)
        if (modal?.onClose) {
          modal.onClose()
        }
        set({ modals: get().modals.filter(m => m.id !== id) })
      },

      closeAllModals: () => {
        const { modals } = get()
        modals.forEach(modal => {
          if (modal.onClose) {
            modal.onClose()
          }
        })
        set({ modals: [] })
      },

      setGlobalLoading: (loading: boolean, text?: string) => {
        set({ globalLoading: loading, loadingText: text || null })
      },

      setCurrentPage: (page: string) => {
        set({ currentPage: page })
      },

      setBreadcrumbs: (breadcrumbs: Array<{ label: string; href?: string }>) => {
        set({ breadcrumbs })
      },

      // Utility toast methods
      showSuccessToast: (message: string, title?: string) => {
        get().addToast({
          type: 'success',
          message,
          title,
          duration: 4000
        })
      },

      showErrorToast: (message: string, title?: string) => {
        get().addToast({
          type: 'error',
          message,
          title,
          duration: 6000
        })
      },

      showWarningToast: (message: string, title?: string) => {
        get().addToast({
          type: 'warning',
          message,
          title,
          duration: 5000
        })
      },

      showInfoToast: (message: string, title?: string) => {
        get().addToast({
          type: 'info',
          message,
          title,
          duration: 4000
        })
      }
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        preferences: state.preferences
      }),
      onRehydrateStorage: () => (state) => {
        // Apply theme on rehydration
        if (state?.theme) {
          const root = window.document.documentElement
          
          if (state.theme === 'system') {
            const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
            root.classList.toggle('dark', systemTheme === 'dark')
          } else {
            root.classList.toggle('dark', state.theme === 'dark')
          }
        }
      }
    }
  )
)