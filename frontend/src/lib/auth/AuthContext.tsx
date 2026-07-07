'use client'

import { createContext, useContext, useEffect, useState } from 'react'

import { getMe, type User } from '@/lib/api/auth'
import { clearToken, getToken, setToken } from '@/lib/auth/storage'

type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (token: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Hydrate on mount: a stored token means a session may exist, so resolve it
  // to the current user via /auth/me. A stale token (401) is cleared.
  useEffect(() => {
    const token = getToken()
    if (!token) {
      setLoading(false)
      return
    }
    getMe(token)
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  async function login(token: string) {
    setToken(token)
    setUser(await getMe(token))
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
