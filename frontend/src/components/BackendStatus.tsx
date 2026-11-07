import { useCallback, useEffect, useState } from 'react'
import { getApiBaseUrl } from '../api/client'
import { fetchHealth } from '../api/health'
import { ApiError, type HealthResponse } from '../api/types'

type LoadState = 'loading' | 'success' | 'error'

interface StatusView {
  state: LoadState
  health: HealthResponse | null
  errorMessage: string | null
}

const initialView: StatusView = {
  state: 'loading',
  health: null,
  errorMessage: null,
}

function formatPostgis(health: HealthResponse | null): string {
  if (!health) {
    return 'Unknown'
  }
  if (health.postgis == null || health.postgis === '') {
    return 'Not reported by API'
  }
  return health.postgis
}

export function BackendStatus() {
  const [view, setView] = useState<StatusView>(initialView)

  const refresh = useCallback(async () => {
    try {
      const health = await fetchHealth()
      setView({ state: 'success', health, errorMessage: null })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'Unexpected error while checking backend health.'
      setView({ state: 'error', health: null, errorMessage: message })
    }
  }, [])

  // External-system sync: fetch on mount. State is only set after `await`,
  // so this is not a synchronous cascading render.
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    void refresh()
  }, [refresh])

  const handleRefresh = () => {
    setView({ state: 'loading', health: null, errorMessage: null })
    void refresh()
  }

  const connected = view.state === 'success'
  const healthy = connected && view.health?.status === 'healthy'
  const databaseLabel = view.health?.database ?? 'unavailable'

  return (
    <section className="status-panel" aria-live="polite">
      <div className="status-panel-header">
        <h2>Backend connectivity</h2>
        <button type="button" className="refresh-button" onClick={handleRefresh}>
          Refresh
        </button>
      </div>

      <p className="status-meta">
        API base: <code>{getApiBaseUrl()}</code>
      </p>

      {view.state === 'loading' && (
        <p className="status-banner status-banner-loading">Checking Django health endpoint…</p>
      )}

      {view.state === 'error' && (
        <p className="status-banner status-banner-error" role="alert">
          {view.errorMessage}
        </p>
      )}

      {view.state === 'success' && healthy && (
        <p className="status-banner status-banner-success">Backend connected.</p>
      )}

      {view.state === 'success' && !healthy && (
        <p className="status-banner status-banner-error" role="alert">
          Backend reached, but overall status is {view.health?.status ?? 'unhealthy'}.
        </p>
      )}

      <dl className="status-grid">
        <div>
          <dt>Backend</dt>
          <dd data-tone={connected ? 'ok' : view.state === 'loading' ? 'pending' : 'bad'}>
            {view.state === 'loading'
              ? 'Checking…'
              : connected
                ? 'Connected'
                : 'Unavailable'}
          </dd>
        </div>
        <div>
          <dt>Database</dt>
          <dd data-tone={databaseLabel === 'connected' ? 'ok' : view.state === 'loading' ? 'pending' : 'bad'}>
            {view.state === 'loading' ? 'Checking…' : databaseLabel}
          </dd>
        </div>
        <div>
          <dt>PostGIS</dt>
          <dd data-tone={view.state === 'loading' ? 'pending' : 'neutral'}>
            {view.state === 'loading' ? 'Checking…' : formatPostgis(view.health)}
          </dd>
        </div>
        <div>
          <dt>Checked at</dt>
          <dd data-tone="neutral">
            {view.health?.timestamp ?? (view.state === 'loading' ? '—' : 'n/a')}
          </dd>
        </div>
      </dl>
    </section>
  )
}
