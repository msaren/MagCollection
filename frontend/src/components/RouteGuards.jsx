import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

// Layout routes: rendered via <Route element={<RequireAuth />}> wrapping child
// routes, so <Outlet /> renders whichever child route matched.

export function RequireAuth() {
  const { user, loading } = useAuth()
  if (loading) return <div className="page-loading">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}

export function RequireAdmin() {
  const { isAdmin, loading } = useAuth()
  if (loading) return <div className="page-loading">Loading…</div>
  if (!isAdmin) return <Navigate to="/" replace />
  return <Outlet />
}
