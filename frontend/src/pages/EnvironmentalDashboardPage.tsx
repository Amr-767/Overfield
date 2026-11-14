import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  DEFAULT_WINDOW_DAYS,
  getEnvironmentSummary,
} from '../api/environment'
import { getFarm, listFarms } from '../api/farms'
import { ApiError } from '../api/types'
import { Banner } from '../components/Field'
import { IndicatorCard } from '../components/environment/IndicatorCard'
import { ScanPanel } from '../components/environment/ScanPanel'
import { formatHectares } from '../lib/format'
import {
  formatTimestamp,
  freshnessLabel,
  freshnessTone,
  statusLabel,
  statusTone,
} from '../lib/environment'

function errorText(error: unknown): string {
  if (!(error instanceof ApiError)) return 'An unexpected error occurred. Please try again.'
  if (error.status === 401) return 'Your session has expired. Sign in again to continue.'
  if (error.status === 403 || error.status === 404) {
    return 'This farm does not exist or belongs to another account.'
  }
  return error.message
}

export function EnvironmentalDashboardPage() {
  const { farmId } = useParams()
  const id = Number(farmId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const farmQuery = useQuery({
    queryKey: ['farm', id],
    queryFn: () => getFarm(id),
    enabled: Number.isFinite(id),
  })
  const farmsQuery = useQuery({
    queryKey: ['farms'],
    queryFn: listFarms,
    enabled: Number.isFinite(id),
  })
  const summaryQuery = useQuery({
    queryKey: ['farm', id, 'environment', 'current', DEFAULT_WINDOW_DAYS],
    queryFn: () => getEnvironmentSummary(id, DEFAULT_WINDOW_DAYS),
    enabled: Number.isFinite(id) && farmQuery.isSuccess,
  })

  const refreshSummary = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['farm', id, 'environment'] })
  }, [queryClient, id])

  if (!Number.isFinite(id)) {
    return (
      <div className="page">
        <Banner tone="error" title="Invalid farm">
          Choose a farm from your farm list.
        </Banner>
        <Link to="/farms" className="button button-ghost">
          Back to my farms
        </Link>
      </div>
    )
  }

  if (farmQuery.isPending) {
    return (
      <div className="page">
        <p className="page-loading" role="status">
          Loading farm…
        </p>
      </div>
    )
  }

  if (farmQuery.isError) {
    const notFound = farmQuery.error instanceof ApiError && farmQuery.error.status === 404
    return (
      <div className="page">
        <Banner tone="error" title={notFound ? 'Farm not found' : 'Could not load this farm'}>
          {notFound
            ? 'This farm does not exist or belongs to another account.'
            : errorText(farmQuery.error)}
        </Banner>
        <Link to="/farms" className="button button-ghost">
          Back to my farms
        </Link>
      </div>
    )
  }

  const farm = farmQuery.data
  const summary = summaryQuery.data
  const summaryStatus =
    summaryQuery.error instanceof ApiError ? summaryQuery.error.status : undefined
  const fatalSummaryError = summaryStatus === 401 || summaryStatus === 403 || summaryStatus === 404
  const farms = farmsQuery.data?.results ?? []
  const hasObservations = summary?.window.latest_observation != null

  return (
    <div className="page env-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/farms">My farms</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/farms/${farm.id}`}>{farm.name}</Link>
        <span aria-hidden="true">/</span>
        <span>Environmental dashboard</span>
      </nav>

      <header className="page-header env-page-header">
        <div>
          <p className="step-kicker">Farm environmental dashboard</p>
          <h1 className="page-title">{farm.name}</h1>
          <p className="page-lead">
            {[farm.region_code, farm.country_code].filter(Boolean).join(', ') || 'No region'} ·{' '}
            {formatHectares(farm.area_hectares)} · NASA POWER environmental evidence
          </p>
        </div>
        <div className="env-header-actions">
          <label className="field env-farm-switch" htmlFor="environment-farm">
            <span className="field-label">Switch farm</span>
            <select
              id="environment-farm"
              className="input"
              value={farm.id}
              onChange={(event) => navigate(`/farms/${event.target.value}/environment`)}
            >
              {farms.length === 0 ? <option value={farm.id}>{farm.name}</option> : null}
              {farms.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.region_code || 'No region'}
                </option>
              ))}
            </select>
          </label>
          <Link to={`/farms/${farm.id}`} className="button button-ghost">
            Farm details
          </Link>
        </div>
      </header>

      {farmsQuery.isError ? (
        <Banner tone="warning" title="Could not load your other farms">
          This dashboard still shows the selected farm. {errorText(farmsQuery.error)}
        </Banner>
      ) : null}

      {summaryQuery.isPending ? (
        <p className="page-loading" role="status">
          Reading environmental summary…
        </p>
      ) : null}

      {summaryQuery.isError && fatalSummaryError ? (
        <Banner tone="error" title="Environmental summary unavailable">
          {errorText(summaryQuery.error)}
        </Banner>
      ) : null}

      {summary ? (
        <section className="env-panel env-overview" aria-labelledby="env-overview-title">
          <div className="env-panel-head">
            <div>
              <p className="step-kicker">Environmental summary</p>
              <h2 id="env-overview-title">What the stored observations show</h2>
            </div>
            <div className="env-tags">
              <span className={`env-tag env-tag-${statusTone(summary.data_status)}`}>
                {statusLabel(summary.data_status)}
              </span>
              <span className={`env-tag env-tag-${freshnessTone(summary.freshness.status)}`}>
                {freshnessLabel(summary.freshness.status)}
              </span>
            </div>
          </div>

          <dl className="env-overview-grid">
            <div>
              <dt>Analysis window</dt>
              <dd>
                {summary.window.start} → {summary.window.end}
              </dd>
              <small>{summary.window.days} days, ending at the latest observation</small>
            </div>
            <div>
              <dt>Latest observation</dt>
              <dd>{summary.window.latest_observation ?? 'None stored'}</dd>
              <small>
                {summary.window.age_days === null
                  ? 'Data age cannot be determined'
                  : `${summary.window.age_days} day(s) before generation`}
              </small>
            </div>
            <div>
              <dt>Generated</dt>
              <dd>{formatTimestamp(summary.generated_at)}</dd>
              <small>UTC</small>
            </div>
            <div>
              <dt>Score</dt>
              <dd>Not assessed</dd>
              <small>No 0–100 suitability score exists for these indicators</small>
            </div>
          </dl>

          <p className="env-notice">
            Environmental values are NASA POWER MERRA-2 grid-cell estimates for the farm&apos;s
            representative point. They are not on-farm measurements and are not a forecast. This
            window ends at the newest stored observation, never at &ldquo;today&rdquo;.
          </p>

          {summary.limitations.length > 0 ? (
            <details className="env-details">
              <summary>Summary limitations ({summary.limitations.length})</summary>
              <ul className="env-list">
                {summary.limitations.map((limitation, index) => (
                  <li key={index}>{limitation}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </section>
      ) : null}

      {summaryQuery.isError && !fatalSummaryError ? (
        <Banner tone="error" title="Could not load the environmental summary">
          {errorText(summaryQuery.error)}{' '}
          <button
            type="button"
            className="link-button"
            onClick={() => void summaryQuery.refetch()}
          >
            Try again
          </button>
        </Banner>
      ) : null}

      {!fatalSummaryError ? (
        <ScanPanel farmId={farm.id} onSummaryRefresh={refreshSummary} />
      ) : null}

      {summary && !hasObservations ? (
        <Banner tone="warning" title="No environmental observations stored yet">
          The farm is registered, but no NASA POWER observation is available for it. Request a
          scan above. Until a scan stores data, WATER and HEAT stay insufficient, and nothing is
          filled in from regional averages or demo values.
        </Banner>
      ) : null}

      {summary ? (
        <>
          <section aria-labelledby="env-indicators-title">
            <div className="env-section-head">
              <div>
                <p className="step-kicker">Four environmental indicators</p>
                <h2 id="env-indicators-title">Source-labelled status, not a score</h2>
              </div>
              <p className="env-muted">
                Status describes whether the indicator could be assessed. Missing values stay
                missing.
              </p>
            </div>
            <div className="env-grid">
              <IndicatorCard indicator={summary.indicators.water} index={1} />
              <IndicatorCard indicator={summary.indicators.heat} index={2} />
              <IndicatorCard indicator={summary.indicators.soil} index={3} />
              <IndicatorCard indicator={summary.indicators.market} index={4} />
            </div>
          </section>

          <section className="env-panel env-next" aria-labelledby="env-next-title">
            <div>
              <p className="step-kicker">Continue the journey</p>
              <h2 id="env-next-title">From evidence to planning</h2>
            </div>
            <div className="env-next-grid">
              <article>
                <h3>Rotation assessment</h3>
                <p>
                  No approved Gharbia crop catalogue or season calendar exists yet, so the
                  rotation engine returns <code>INSUFFICIENT_EVIDENCE</code> with named missing
                  inputs. It will not invent strategies or crop traits.
                </p>
                <Link className="button button-ghost" to="/rotation">
                  Open rotation explorer
                </Link>
              </article>
              <article>
                <h3>Hypothetical scenarios</h3>
                <p>
                  The scenario lab applies bounded user-declared adjustments to stored
                  observations. Every output remains labelled <code>HYPOTHETICAL</code>; it is not
                  a NASA forecast.
                </p>
                <Link className="button button-ghost" to="/simulations">
                  Open scenario lab
                </Link>
              </article>
            </div>
          </section>
        </>
      ) : null}
    </div>
  )
}
