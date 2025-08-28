'use client'

import React, { createContext, useContext, useEffect } from 'react'
import { useAuthStore } from '@/store/auth'
import { socketManager, useSocket } from '@/lib/socket'

interface SocketContextType {
  isConnected: boolean
  socket: typeof socketManager
}

const SocketContext = createContext<SocketContextType>({
  isConnected: false,
  socket: socketManager,
})

export function useSocketContext() {
  return useContext(SocketContext)
}

interface SocketProviderProps {
  children: React.ReactNode
}

export function SocketProvider({ children }: SocketProviderProps) {
  const { isAuthenticated } = useAuthStore()
  const socket = useSocket()
  const [isConnected, setIsConnected] = React.useState(false)

  useEffect(() => {
    const checkConnection = () => {
      setIsConnected(socket.isConnected())
    }

    // Check connection status periodically
    const interval = setInterval(checkConnection, 1000)

    // Initial check
    checkConnection()

    return () => clearInterval(interval)
  }, [socket])

  useEffect(() => {
    if (isAuthenticated) {
      socket.connect()
    } else {
      socket.disconnect()
    }
  }, [isAuthenticated, socket])

  const contextValue: SocketContextType = {
    isConnected,
    socket,
  }

  return (
    <SocketContext.Provider value={contextValue}>
      {children}
    </SocketContext.Provider>
  )
}