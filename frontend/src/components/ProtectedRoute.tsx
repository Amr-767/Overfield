import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../auth/auth-context'

export function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return <p className="page-loading">Checking your session…</p>
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
