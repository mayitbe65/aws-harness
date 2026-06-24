import React, { createContext, useState, useEffect, type ReactNode } from 'react'
import api from '@/services/api'
import { storage } from '@/utils/storage'
import type { User, LoginResponse } from '@/types/api'

interface AuthContextType {
  currentUser: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  clearError: () => void
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Initialize from localStorage on mount
  useEffect(() => {
    const initializeAuth = () => {
      const token = storage.getToken()
      if (token) {
        const user = storage.getUser()
        if (user) {
          setCurrentUser(user)
        }
      }
      setIsLoading(false)
    }

    initializeAuth()
  }, [])

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await api.post<LoginResponse>('/api/auth/login', {
        email,
        password,
      })

      const { access_token, user_id, role } = response.data

      const userData: User = {
        user_id,
        email,
        name: email,
        role: (role as 'admin' | 'student'),
      }

      storage.setToken(access_token)
      storage.setUser(userData)
      setCurrentUser(userData)
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      const message = error.response?.data?.detail || 'Login failed'
      setError(message)
      throw err
    } finally {
      setIsLoading(false)
    }
  }

  const logout = (): void => {
    storage.clear()
    setCurrentUser(null)
    setError(null)
  }

  const clearError = (): void => {
    setError(null)
  }

  const value: AuthContextType = {
    currentUser,
    isAuthenticated: !!currentUser,
    isLoading,
    error,
    login,
    logout,
    clearError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
