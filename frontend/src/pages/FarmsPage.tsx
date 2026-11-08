import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { listFarms } from '../api/farms'
import { ApiError } from '../api/types'
import { Banner } from '../components/Field'
import { areaSourceLabel, formatDate, formatHectares } from '../lib/format'

export function FarmsPage() {
  const farmsQuery = useQuery({ queryKey: ['farms'], queryFn: listFarms })

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="step-kicker">Your account</p>
          <h2 className="page-title">My farms</h2>
          <p className="page-lead">Farm boundaries and areas loaded from your database records.</p>
        </div>
        <Link to="/onboarding" className="button button-primary">
          Add a farm
        </Link>
      </header>

      {farmsQuery.isPending ? <p className="page-loading">Loading your farms…</p> : null}

      {farmsQuery.isError ? (
        <Banner tone="error" title="Could not load farms">
          {farmsQuery.error instanceof ApiError
            ? farmsQuery.error.message
            : 'An unexpected error occurred.'}{' '}
          <button type="button" className="link-button" onClick={() => void farmsQuery.refetch()}>
            Try again
          </button>
        </Banner>
      ) : null}

      {farmsQuery.isSuccess && farmsQuery.data.count === 0 ? (
        <section className="empty-state">
          <h3>No farms yet</h3>
          <p>Draw your first field boundary to see its measured area.</p>
          <Link to="/onboarding" className="button button-primary">
            Start onboarding
          </Link>
        </section>
      ) : null}

      {farmsQuery.isSuccess && farmsQuery.data.count > 0 ? (
        <ul className="farm-grid">
          {farmsQuery.data.results.map((farm) => (
            <li key={farm.id}>
              <Link to={`/farms/${farm.id}`} className="farm-card">
                <div className="farm-card-head">
                  <h3>{farm.name}</h3>
                  <span
                    className={`precision-badge precision-${farm.spatial_precision.toLowerCase()}`}
                  >
                    {farm.spatial_precision === 'HIGH' ? 'Boundary' : 'Point only'}
                  </span>
                </div>
                <p className="farm-card-area">{formatHectares(farm.area_hectares)}</p>
                <p className="farm-card-meta">{areaSourceLabel(farm.area_source)}</p>
                <p className="farm-card-meta">
                  {[farm.region_code, farm.country_code].filter(Boolean).join(', ') || 'No region'} ·{' '}
                  {farm.zone_count} zone{farm.zone_count === 1 ? '' : 's'}
                </p>
                <p className="farm-card-date">Added {formatDate(farm.created_at)}</p>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
