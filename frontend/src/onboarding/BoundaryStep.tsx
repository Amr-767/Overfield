import { useEffect, useState } from 'react'

import { validateBoundary } from '../api/farms'
import { ApiError, type BoundaryGeometry, type PointGeometry } from '../api/types'
import { Banner, Field } from '../components/Field'
import { FarmMap } from '../components/FarmMap'
import { formatHectares } from '../lib/format'
import type { OnboardingDraft } from '../lib/onboarding'

interface StepProps {
  draft: OnboardingDraft
  errors: Record<string, string>
  onChange: (patch: Partial<OnboardingDraft>) => void
}

type AreaState =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'ok'; area: string }
  | { status: 'error'; message: string }

export function BoundaryStep({ draft, errors, onChange }: StepProps) {
  const [areaState, setAreaState] = useState<AreaState>({ status: 'idle' })
  const [geoState, setGeoState] = useState<'idle' | 'locating' | 'error'>('idle')
  const [clearSignal, setClearSignal] = useState(0)

  const boundary = draft.boundary
  const mode = draft.mode
  const visibleAreaState: AreaState =
    mode === 'boundary' && boundary ? areaState : { status: 'idle' }

  // Area always comes from the backend so the preview matches what will be saved.
  useEffect(() => {
    if (mode !== 'boundary' || !boundary) {
      return
    }

    const controller = new AbortController()
    const timer = setTimeout(async () => {
      setAreaState({ status: 'checking' })
      try {
        const result = await validateBoundary(boundary, controller.signal)
        if (controller.signal.aborted) return
        setAreaState({ status: 'ok', area: result.area_hectares })
        onChange({ boundaryAreaHa: result.area_hectares })
      } catch (error) {
        if (controller.signal.aborted) return
        const message =
          error instanceof ApiError
            ? error.message
            : 'The boundary could not be measured. Please redraw it.'
        setAreaState({ status: 'error', message })
        onChange({ boundaryAreaHa: null })
      }
    }, 450)

    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [boundary, mode, onChange])

  const handleBoundaryChange = (next: BoundaryGeometry | null) => {
    onChange({ boundary: next, boundaryAreaHa: next ? draft.boundaryAreaHa : null })
  }

  const handleMarkerChange = (marker: PointGeometry) => {
    onChange({ marker })
  }

  const locate = () => {
    if (!navigator.geolocation) {
      setGeoState('error')
      return
    }
    setGeoState('locating')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setGeoState('idle')
        onChange({
          marker: {
            type: 'Point',
            coordinates: [position.coords.longitude, position.coords.latitude],
          },
        })
      },
      () => setGeoState('error'),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  const switchMode = (next: 'boundary' | 'point') => {
    onChange({ mode: next })
  }

  return (
    <section className="step-panel" aria-labelledby="boundary-step-title">
      <header className="step-header">
        <p className="step-kicker">Step 3 of 5</p>
        <h2 id="boundary-step-title">Draw your farm</h2>
        <p className="step-lead">
          Trace the outline of your field on the map. The area is measured by the server from the
          boundary itself.
        </p>
      </header>

      <div className="mode-switch" role="group" aria-label="How do you want to define your farm?">
        <button
          type="button"
          className={`mode-button${mode === 'boundary' ? ' mode-button-active' : ''}`}
          onClick={() => switchMode('boundary')}
        >
          Draw the boundary
          <span>Most accurate</span>
        </button>
        <button
          type="button"
          className={`mode-button${mode === 'point' ? ' mode-button-active' : ''}`}
          onClick={() => switchMode('point')}
        >
          Just a location
          <span>Approximate area</span>
        </button>
      </div>

      <FarmMap
        mode={mode === 'boundary' ? 'draw' : 'point'}
        boundary={mode === 'boundary' ? draft.boundary : null}
        marker={draft.marker}
        clearSignal={clearSignal}
        onBoundaryChange={handleBoundaryChange}
        onMarkerChange={handleMarkerChange}
      />

      <div className="map-toolbar">
        <button type="button" className="button button-ghost" onClick={locate}>
          {geoState === 'locating' ? 'Finding you…' : 'Use my location'}
        </button>
        {mode === 'boundary' && draft.boundary ? (
          <button
            type="button"
            className="button button-ghost"
            onClick={() => {
              setClearSignal((value) => value + 1)
              onChange({ boundary: null, boundaryAreaHa: null })
            }}
          >
            Clear boundary
          </button>
        ) : null}
      </div>

      {geoState === 'error' ? (
        <Banner tone="warning">
          Your location could not be read. You can still tap the map to choose a place.
        </Banner>
      ) : null}

      {errors.boundary ? <Banner tone="error">{errors.boundary}</Banner> : null}
      {errors.marker ? <Banner tone="error">{errors.marker}</Banner> : null}

      {mode === 'boundary' ? (
        <div className="area-readout" aria-live="polite">
          <span className="area-readout-label">Farm area</span>
          {visibleAreaState.status === 'checking' ? (
            <strong className="area-readout-value area-readout-muted">Measuring…</strong>
          ) : visibleAreaState.status === 'ok' ? (
            <>
              <strong className="area-readout-value">{formatHectares(visibleAreaState.area)}</strong>
              <span className="area-readout-note">
                Calculated from your boundary by PostGIS (geodesic area)
              </span>
            </>
          ) : visibleAreaState.status === 'error' ? (
            <span className="area-readout-error">{visibleAreaState.message}</span>
          ) : (
            <span className="area-readout-note">
              Draw a polygon with the toolbar to see the measured area.
            </span>
          )}
        </div>
      ) : (
        <div className="fallback-panel">
          <Field
            id="reported-area"
            label="Approximate farm size (hectares)"
            hint="A rough figure is fine. This is recorded as farmer-reported, not GIS-calculated."
            error={errors.reportedAreaHa}
          >
            <input
              id="reported-area"
              className="input input-narrow"
              inputMode="decimal"
              value={draft.reportedAreaHa}
              placeholder="2.5"
              onChange={(event) => onChange({ reportedAreaHa: event.target.value })}
            />
          </Field>
          <Banner tone="warning" title="Lower spatial precision">
            A single point plus an area estimate is stored with <code>LOW</code> precision and
            marked as farmer-reported. Add a boundary later for field-level analysis.
          </Banner>
        </div>
      )}
    </section>
  )
}
