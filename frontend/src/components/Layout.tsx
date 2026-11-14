import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'

import { useAuth } from '../auth/auth-context'

interface LayoutProps {
  children: ReactNode
  wide?: boolean
}

export function Layout({ children, wide = false }: LayoutProps) {
  const { status, profile, logout } = useAuth()

  return (
    <div className={`app-shell${wide ? ' app-shell-wide' : ''}`}>
      <header className="app-header">
        <div className="app-header-row">
          <Link to="/" className="brand brand-link">
            <span className="brand-mark" aria-hidden="true" />
            <div>
              <p className="brand-kicker">NASA Space Apps</p>
              <h1 className="brand-title">Overfield</h1>
              <p className="brand-tagline">Explore Beyond the Field.</p>
            </div>
          </Link>

          <nav className="app-nav" aria-label="Main navigation">
            {status === 'authenticated' ? (
              <>
                <NavLink to="/farms" className="nav-link">
                  My farms
                </NavLink>
                <NavLink to="/rotation" className="nav-link">
                  Rotation explorer
                </NavLink>
                <NavLink to="/simulations" className="nav-link">
                  Scenario lab
                </NavLink>
                <NavLink to="/onboarding" className="nav-link">
                  Add a farm
                </NavLink>
                <span className="nav-user" title={profile?.email || profile?.username}>
                  {profile?.display_name || profile?.username}
                </span>
                <button type="button" className="nav-button" onClick={logout}>
                  Sign out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="nav-link">
                  Sign in
                </NavLink>
                <NavLink to="/register" className="nav-link nav-link-primary">
                  Create account
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="app-main">{children}</main>

      <footer className="app-footer">
        <p>Overfield — Explore Beyond the Field. Field boundaries stay private to your account.</p>
      </footer>
    </div>
  )
}
