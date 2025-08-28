'use client'

import React from 'react'
import {
  Toast,
  ToastClose,
  ToastDescription,
  ToastProvider as RadixToastProvider,
  ToastTitle,
  ToastViewport,
} from '@/components/ui/toast'
import { useUIStore } from '@/store/ui'
import { CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react'

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const { toasts, removeToast } = useUIStore()

  const getIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-5 w-5" />
      case 'error':
        return <XCircle className="h-5 w-5" />
      case 'warning':
        return <AlertCircle className="h-5 w-5" />
      case 'info':
        return <Info className="h-5 w-5" />
      default:
        return null
    }
  }

  const getVariant = (type: string) => {
    switch (type) {
      case 'success':
        return 'success'
      case 'error':
        return 'destructive'
      case 'warning':
        return 'warning'
      case 'info':
        return 'info'
      default:
        return 'default'
    }
  }

  return (
    <RadixToastProvider>
      {children}
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          variant={getVariant(toast.type) as any}
          duration={toast.persistent ? Infinity : toast.duration}
        >
          <div className="flex items-start space-x-3">
            {getIcon(toast.type)}
            <div className="flex-1 space-y-1">
              {toast.title && <ToastTitle>{toast.title}</ToastTitle>}
              <ToastDescription>{toast.message}</ToastDescription>
              {toast.actions && toast.actions.length > 0 && (
                <div className="flex space-x-2 pt-2">
                  {toast.actions.map((action, index) => (
                    <button
                      key={index}
                      onClick={action.onClick}
                      className="text-sm font-medium underline underline-offset-4 hover:no-underline"
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          <ToastClose onClick={() => removeToast(toast.id)} />
        </Toast>
      ))}
      <ToastViewport />
    </RadixToastProvider>
  )
}