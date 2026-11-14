import { useQuery } from '@tanstack/react-query'
import { Link, useLocation, useParams } from 'react-router-dom'

import { getFarm, getFarmContext, listZones } from '../api/farms'
import { ApiError } from '../api/types'
import { Banner } from '../components/Field'
import { FarmMap } from '../components/FarmMap'
import {
  IRRIGATION_OPTIONS,
  RELIABILITY_OPTIONS,
  TEXTURE_OPTIONS,
  PRIORITY_FIELDS,
} from '../lib/onboarding'
import { areaSourceLabel, formatDate, formatHectares, precisionLabel } from '../lib/format'

function optionLabel(
  options: ReadonlyArray<{ value: string; label: string }>,
  value: string,
): string {
  if (!value) return 'Not provided'
  return options.find((option) => option.value === value)?.label ?? value
}

export function FarmDetailPage() {
  const { farmId } = useParams()
  const location = useLocation()
  const id = Number(farmId)
  const contextWarning = (location.state as { contextError?: string } | null)?.contextError

  const farmQuery = useQuery({
    queryKey: ['farm', id],
    queryFn: () => getFarm(id),
    enabled: Number.isFinite(id),
  })
  const contextQuery = useQuery({
    queryKey: ['farm', id, 'context'],
    queryFn: () => getFarmContext(id),
    enabled: Number.isFinite(id) && farmQuery.isSuccess,
  })
  const zonesQuery = useQuery({
    queryKey: ['farm', id, 'zones'],
    queryFn: () => listZones(id),
    enabled: Number.isFinite(id) && farmQuery.isSuccess,
  })

  if (farmQuery.isPending) {
    return <p className="page-loading">Loading farm…</p>
  }

  if (farmQuery.isError) {
    const notFound = farmQuery.error instanceof ApiError && farmQuery.error.status === 404
    return (
      <div className="page">
        <Banner tone="error" title={notFound ? 'Farm not found' : 'Could not load this farm'}>
          {notFound
            ? 'This farm does not exist or belongs to another account.'
            : farmQuery.error instanceof ApiError
              ? farmQuery.error.message
              : 'An unexpected error occurred.'}
        </Banner>
        <Link to="/farms" className="button button-ghost">
          Back to my farms
        </Link>
      </div>
    )
  }

  const farm = farmQuery.data
  const context = contextQuery.data
  const zones = zonesQuery.data?.results ?? []
  const priorities = context?.priorities ?? {}

  return (
    <div className="page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/farms">My farms</Link>
        <span aria-hidden="true">/</span>
        <span>{farm.name}</span>
      </nav>

      {contextWarning ? (
        <Banner tone="warning" title="Farm saved, but the farm information was not">
          {contextWarning} You can update it here later.
        </Banner>
      ) : null}

      <header className="page-header">
        <div>
          <p className="step-kicker">Saved farm</p>
          <h2 className="page-title">{farm.name}</h2>
          <p className="page-lead">
            {[farm.region_code, farm.country_code].filter(Boolean).join(', ') || 'No region'} · added{' '}
            {formatDate(farm.created_at)}
          </p>
        </div>
        <span className={`precision-badge precision-${farm.spatial_precision.toLowerCase()}`}>
          {precisionLabel(farm.spatial_precision)}
        </span>
        <Link
          to={`/farms/${farm.id}/environment`}
          className="button button-primary"
        >
          Environmental dashboard
        </Link>
      </header>

      <div className="detail-grid">
        <section className="detail-card">
          <h3>Area</h3>
          <p className="detail-big">{formatHectares(farm.area_hectares)}</p>
          <p className="detail-meta">{areaSourceLabel(farm.area_source)}</p>
          <p className="detail-meta">Timezone: {farm.timezone}</p>
          <p className="detail-meta">Zones: {zones.length}</p>
        </section>

        <section className="detail-card detail-card-wide">
          <h3>Boundary</h3>
          <FarmMap
            mode="readonly"
            boundary={farm.boundary}
            marker={farm.location}
            zoom={15}
          />
        </section>
      </div>

      <section className="detail-card">
        <h3>Farm information</h3>
        {contextQuery.isPending ? <p className="page-loading">Loading farm information…</p> : null}
        {contextQuery.isError ? (
          <Banner tone="warning">
            Farm information could not be loaded.{' '}
            <button type="button" className="link-button" onClick={() => void contextQuery.refetch()}>
              Retry
            </button>
          </Banner>
        ) : null}
        {context ? (
          <div className="context-grid">
            <div>
              <h4>Soil</h4>
              <dl className="review-list">
                <div>
                  <dt>Type</dt>
                  <dd>{optionLabel(TEXTURE_OPTIONS, context.texture_class)}</dd>
                </div>
                <div>
                  <dt>pH</dt>
                  <dd>{context.ph ?? 'Not provided'}</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>
                    {context.soil_source === 'LAB_TEST'
                      ? 'Laboratory test'
                      : context.soil_source === 'FARMER_REPORTED'
                        ? 'Farmer-entered'
                        : context.soil_source}
                  </dd>
                </div>
                <div>
                  <dt>Nitrogen (ppm)</dt>
                  <dd>{context.nitrogen_ppm ?? 'Not provided'}</dd>
                </div>
                <div>
                  <dt>Phosphorus (ppm)</dt>
                  <dd>{context.phosphorus_ppm ?? 'Not provided'}</dd>
                </div>
                <div>
                  <dt>Potassium (ppm)</dt>
                  <dd>{context.potassium_ppm ?? 'Not provided'}</dd>
                </div>
              </dl>
            </div>

            <div>
              <h4>Water</h4>
              <dl className="review-list">
                <div>
                  <dt>Irrigation</dt>
                  <dd>
                    {context.irrigation_available === null
                      ? 'Not provided'
                      : context.irrigation_available
                        ? 'Available'
                        : 'Rain-fed'}
                  </dd>
                </div>
                <div>
                  <dt>Method</dt>
                  <dd>{optionLabel(IRRIGATION_OPTIONS, context.irrigation_type)}</dd>
                </div>
                <div>
                  <dt>Reliability</dt>
                  <dd>{optionLabel(RELIABILITY_OPTIONS, context.water_reliability)}</dd>
                </div>
              </dl>
            </div>

            <div>
              <h4>Crops</h4>
              {context.current_crops.length === 0 ? (
                <p className="review-empty">No crops recorded.</p>
              ) : (
                <ul className="review-chips">
                  {context.current_crops.map((entry, index) => (
                    <li key={`${entry.season}-${index}`}>
                      <strong>{entry.crop}</strong>
                      <span>{entry.season}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div>
              <h4>Priorities</h4>
              {Object.keys(priorities).length === 0 ? (
                <p className="review-empty">No priorities recorded.</p>
              ) : (
                <ul className="review-weights">
                  {PRIORITY_FIELDS.filter((field) => priorities[field.apiKey] !== undefined).map(
                    (field) => (
                      <li key={field.key}>
                        <span>{field.label}</span>
                        <span>{Math.round((priorities[field.apiKey] ?? 0) * 100)}%</span>
                      </li>
                    ),
                  )}
                </ul>
              )}
              {context.constraints?.equipment?.length ? (
                <p className="review-empty">
                  Limitations: {context.constraints.equipment.join(', ').replace(/_/g, ' ')}
                </p>
              ) : null}
            </div>
          </div>
        ) : null}
      </section>

      <section className="detail-card">
        <h3>Zones</h3>
        {zones.length === 0 ? (
          <p className="review-empty">
            No zones yet. Zones are optional — use them when parts of the farm have different crops,
            soil or irrigation.
          </p>
        ) : (
          <ul className="zone-list">
            {zones.map((zone) => (
              <li key={zone.id}>
                <strong>{zone.name}</strong>
                <span>{formatHectares(zone.area_hectares)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
