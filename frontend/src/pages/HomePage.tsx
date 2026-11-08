import { Link } from 'react-router-dom'

import { useAuth } from '../auth/auth-context'
import { BackendStatus } from '../components/BackendStatus'

export function HomePage() {
  const { status } = useAuth()
  const authenticated = status === 'authenticated'

  return (
    <div className="home">
      <section className="hero">
        <div className="hero-copy">
          <p className="hero-kicker">NASA Space Apps · Field Shift</p>
          <h2 className="hero-title">Know your land before you plan the season.</h2>
          <p className="hero-lead">
            Map your field, record what you already know about your soil and water, and get an
            honest starting point for crop decisions — with the area measured from your own
            boundary.
          </p>
          <div className="hero-actions">
            {authenticated ? (
              <>
                <Link to="/onboarding" className="button button-primary button-large">
                  Add a farm
                </Link>
                <Link to="/farms" className="button button-ghost button-large">
                  My farms
                </Link>
              </>
            ) : (
              <>
                <Link to="/register" className="button button-primary button-large">
                  Create account
                </Link>
                <Link to="/login" className="button button-ghost button-large">
                  Sign in
                </Link>
              </>
            )}
          </div>
        </div>
        <ul className="hero-points">
          <li>
            <strong>Draw or pin your field</strong>
            <span>Use the map, or fall back to a location and approximate area.</span>
          </li>
          <li>
            <strong>Area you can trust</strong>
            <span>Measured on the server with PostGIS, never guessed from degrees.</span>
          </li>
          <li>
            <strong>Only what you know</strong>
            <span>Unknown soil values stay unknown — nothing is invented for you.</span>
          </li>
        </ul>
      </section>

      <BackendStatus />
    </div>
  )
}
