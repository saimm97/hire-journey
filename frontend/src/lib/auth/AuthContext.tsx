'use client'

import { createContext, useContext, useEffect, useState } from 'react'

import { getMe, logoutUser, type User } from '@/lib/api/auth'

type AuthContextValue = {
  user: User | null
  loading: boolean
  login: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Hydrate on mount: check if the browser has a valid HTTP cookie
  // session by querying the /auth/me endpoint.
  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  async function login() {
    setUser(await getMe())
  }

  async function logout() {
    try {
      await logoutUser()
    } catch (e) {
      console.error('Failed to log out on server:', e)
    } finally {
      setUser(null)
    }
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
