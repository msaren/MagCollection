import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api, getToken, setToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Resolves a stored token into a user on load/refresh. Any failure (expired,
  // tampered, or the account was deleted server-side) just drops back to logged-out
  // rather than surfacing an error, since there's no session to recover here.
  const loadUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await api.me()
      setUser(me)
    } catch {
      setToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUser()
  }, [loadUser])

  const login = useCallback(async (username, password) => {
    const { token, user: loggedInUser } = await api.login(username, password)
    setToken(token)
    setUser(loggedInUser)
    return loggedInUser
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const setTheme = useCallback(async (theme) => {
    const updated = await api.updateTheme(theme)
    setUser(updated)
    return updated
  }, [])

  // The theme is stored per-user server-side; mirror it onto the root element so
  // index.css's [data-theme='dark'] overrides can apply without prop-drilling.
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', user?.theme || 'light')
  }, [user?.theme])

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, setTheme, isAdmin: user?.role === 'admin' }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
