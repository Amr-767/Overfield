import { Banner } from '../components/Field'
import { FarmMap } from '../components/FarmMap'
import { formatHectares } from '../lib/format'
import {
  PRIORITY_FIELDS,
  TEXTURE_OPTIONS,
  IRRIGATION_OPTIONS,
  RELIABILITY_OPTIONS,
  draftAreaSummary,
  normalizePriorities,
  type OnboardingDraft,
} from '../lib/onboarding'

interface ReviewStepProps {
  draft: OnboardingDraft
  onEdit: (stepIndex: number) => void
  onSave: () => void
  saving: boolean
  saveError: string | null
  backendFieldErrors: Record<string, string>
}

function optionLabel(
  options: ReadonlyArray<{ value: string; label: string }>,
  value: string,
): string {
  if (!value) return 'Not provided'
  return options.find((option) => option.value === value)?.label ?? value
}

export function ReviewStep({
  draft,
  onEdit,
  onSave,
  saving,
  saveError,
  backendFieldErrors,
}: ReviewStepProps) {
  const area = draftAreaSummary(draft)
  const weights = normalizePriorities(draft.priorities)
  const crops = draft.crops.filter((entry) => entry.season.trim() && entry.crop.trim())

  const soilRows = [
    { label: 'Soil type', value: optionLabel(TEXTURE_OPTIONS, draft.soil.textureClass) },
    { label: 'pH', value: draft.soil.ph || 'Not provided' },
    {
      label: 'Soil information from',
      value: draft.soil.source === 'LAB_TEST' ? 'A soil test / laboratory' : 'Your own knowledge',
    },
    { label: 'Nitrogen (ppm)', value: draft.soil.nitrogen || 'Not provided' },
    { label: 'Phosphorus (ppm)', value: draft.soil.phosphorus || 'Not provided' },
    { label: 'Potassium (ppm)', value: draft.soil.potassium || 'Not provided' },
  ]

  const waterRows = [
    {
      label: 'Irrigation available',
      value:
        draft.water.irrigationAvailable === ''
          ? 'Not provided'
          : draft.water.irrigationAvailable === 'yes'
            ? 'Yes'
            : 'No, rain-fed',
    },
    {
      label: 'Irrigation method',
      value: optionLabel(IRRIGATION_OPTIONS, draft.water.irrigationType),
    },
    {
      label: 'Water reliability',
      value: optionLabel(RELIABILITY_OPTIONS, draft.water.reliability),
    },
  ]

  const constraintLabels: string[] = []
  if (draft.constraints.noMachinery) constraintLabels.push('No mechanised harvester')
  if (draft.constraints.familyLaborOnly) constraintLabels.push('Family labour only')
  if (draft.constraints.seedAvailability !== 'unknown') {
    constraintLabels.push(
      draft.constraints.seedAvailability === 'available_locally'
        ? 'Seeds available locally'
        : 'Seeds hard to source',
    )
  }

  return (
    <section className="step-panel" aria-labelledby="review-step-title">
      <header className="step-header">
        <p className="step-kicker">Step 5 of 5</p>
        <h2 id="review-step-title">Review and save</h2>
        <p className="step-lead">
          Check everything before saving. You can go back and correct any section.
        </p>
      </header>

      {saveError ? (
        <Banner tone="error" title="We could not save this farm">
          {saveError}
        </Banner>
      ) : null}

      {Object.keys(backendFieldErrors).length > 0 ? (
        <Banner tone="error" title="The server rejected some values">
          <ul className="error-list">
            {Object.entries(backendFieldErrors).map(([field, message]) => (
              <li key={field}>
                <strong>{field.replace(/_/g, ' ')}:</strong> {message}
              </li>
            ))}
          </ul>
        </Banner>
      ) : null}

      <div className="review-grid">
        <article className="review-card">
          <div className="review-card-head">
            <h3>Farm</h3>
            <button type="button" className="link-button" onClick={() => onEdit(1)}>
              Edit
            </button>
          </div>
          <dl className="review-list">
            <div>
              <dt>Name</dt>
              <dd>{draft.farm.name || '—'}</dd>
            </div>
            <div>
              <dt>Country</dt>
              <dd>{draft.farm.countryCode || '—'}</dd>
            </div>
            <div>
              <dt>Region</dt>
              <dd>{draft.farm.regionCode || 'Not provided'}</dd>
            </div>
            <div>
              <dt>Timezone</dt>
              <dd>{draft.farm.timezone || '—'}</dd>
            </div>
          </dl>
        </article>

        <article className="review-card">
          <div className="review-card-head">
            <h3>Location and area</h3>
            <button type="button" className="link-button" onClick={() => onEdit(2)}>
              Edit
            </button>
          </div>
          <dl className="review-list">
            <div>
              <dt>Area</dt>
              <dd>{formatHectares(area.hectares)}</dd>
            </div>
            <div>
              <dt>Area source</dt>
              <dd>{area.label}</dd>
            </div>
            <div>
              <dt>Spatial precision</dt>
              <dd>{area.precision === 'HIGH' ? 'High — drawn boundary' : 'Low — point only'}</dd>
            </div>
          </dl>
        </article>

        <article className="review-card">
          <div className="review-card-head">
            <h3>Soil</h3>
            <button type="button" className="link-button" onClick={() => onEdit(3)}>
              Edit
            </button>
          </div>
          <dl className="review-list">
            {soilRows.map((row) => (
              <div key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="review-card">
          <div className="review-card-head">
            <h3>Water</h3>
            <button type="button" className="link-button" onClick={() => onEdit(3)}>
              Edit
            </button>
          </div>
          <dl className="review-list">
            {waterRows.map((row) => (
              <div key={row.label}>
                <dt>{row.label}</dt>
                <dd>{row.value}</dd>
              </div>
            ))}
          </dl>
        </article>

        <article className="review-card">
          <div className="review-card-head">
            <h3>Current crops</h3>
            <button type="button" className="link-button" onClick={() => onEdit(3)}>
              Edit
            </button>
          </div>
          {crops.length === 0 ? (
            <p className="review-empty">No crops added yet.</p>
          ) : (
            <ul className="review-chips">
              {crops.map((entry, index) => (
                <li key={`${entry.season}-${entry.crop}-${index}`}>
                  <strong>{entry.crop}</strong>
                  <span>{entry.season}</span>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="review-card">
          <div className="review-card-head">
            <h3>Priorities</h3>
            <button type="button" className="link-button" onClick={() => onEdit(3)}>
              Edit
            </button>
          </div>
          {Object.keys(weights).length === 0 ? (
            <p className="review-empty">No priorities set — that is fine.</p>
          ) : (
            <ul className="review-weights">
              {PRIORITY_FIELDS.filter((field) => weights[field.apiKey] !== undefined).map(
                (field) => (
                  <li key={field.key}>
                    <span>{field.label}</span>
                    <span>{Math.round((weights[field.apiKey] ?? 0) * 100)}%</span>
                  </li>
                ),
              )}
            </ul>
          )}
          <p className="review-empty">
            {constraintLabels.length > 0
              ? `Limitations: ${constraintLabels.join(' · ')}`
              : 'No limitations listed.'}
          </p>
        </article>
      </div>

      <div className="review-map">
        <FarmMap
          mode="readonly"
          boundary={draft.mode === 'boundary' ? draft.boundary : null}
          marker={draft.marker}
          zoom={15}
        />
      </div>

      {draft.mode === 'point' ? (
        <Banner tone="warning" title="This farm uses the approximate location method">
          The area is the value you entered and is stored as farmer-reported, not GIS-calculated.
        </Banner>
      ) : null}

      <div className="review-actions">
        <button type="button" className="button button-primary button-large" onClick={onSave} disabled={saving}>
          {saving ? 'Saving your farm…' : 'Save farm'}
        </button>
      </div>
    </section>
  )
}
