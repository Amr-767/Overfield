import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { listFarms } from '../api/farms'
import {
  createSimulation,
  listSimulations,
  type CreateSimulationPayload,
  type ScenarioMode,
  type SimulationMetricValue,
  type SimulationRun,
  type SimulationStep,
} from '../api/simulations'
import { ApiError } from '../api/types'
import { Banner } from '../components/Field'
import { formatDate } from '../lib/format'

import '../simulation.css'

const MODE_OPTIONS: Array<{ value: ScenarioMode; label: string; hint: string }> = [
  {
    value: 'BASELINE',
    label: 'Baseline — no adjustment',
    hint: 'Reproduces the stored observations unchanged.',
  },
  {
    value: 'HOT_SCENARIO',
    label: 'Hot scenario — +2 °C',
    hint: 'Adds 2.00 °C to every stored temperature value.',
  },
  {
    value: 'DRY_SCENARIO',
    label: 'Dry scenario — rainfall × 0.7',
    hint: 'Multiplies stored rainfall by 0.70.',
  },
  {
    value: 'CUSTOM',
    label: 'Custom — choose your own bounds',
    hint: 'Temperature −5 to +5 °C; rainfall multiplier 0.20 to 2.00.',
  },
]

const METRICS: Array<{ key: string; label: string; unit: string }> = [
  { key: 'mean_temperature_c', label: 'Mean temperature', unit: '°C' },
  { key: 'mean_max_temperature_c', label: 'Mean daily maximum', unit: '°C' },
  { key: 'mean_min_temperature_c', label: 'Mean daily minimum', unit: '°C' },
  { key: 'rainfall_total_mm', label: 'Rainfall total', unit: 'mm' },
  { key: 'rainy_days', label: 'Rainy days (≥ 1.0 mm)', unit: '' },
  { key: 'hot_days_max_temperature_ge_35c', label: 'Hot days (max ≥ 35 °C)', unit: '' },
  { key: 'very_hot_days_max_temperature_ge_40c', label: 'Very hot days (max ≥ 40 °C)', unit: '' },
  { key: 'cool_nights_min_temperature_le_5c', label: 'Cool nights (min ≤ 5 °C)', unit: '' },
  { key: 'days_with_mean_temperature', label: 'Days with mean temperature', unit: '' },
  { key: 'days_with_rainfall', label: 'Days with rainfall recorded', unit: '' },
]

function displayError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'An unexpected error occurred. Please try again.'
  if (error.status === 401) return 'Your session has expired. Sign in again to continue.'
  if (error.status === 403 || error.status === 404) {
    return 'This resource is unavailable for your account. Check farm access and try again.'
  }
  const fieldErrors = Object.values(error.fieldMessages)
  if (fieldErrors.length > 0) return fieldErrors.join(' ')
  return error.message
}

function metricValue(value: SimulationMetricValue | undefined, unit = ''): string {
  if (value === null || value === undefined || value === '') return 'Not available'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function freshnessLabel(value: string): string {
  if (value === 'FRESH') return 'Fresh'
  if (value === 'RECENT') return 'Recent'
  if (value === 'STALE') return 'Stale'
  return 'Unknown'
}

function MetricGrid({ metrics }: { metrics: Record<string, SimulationMetricValue> }) {
  return (
    <dl className="simulation-metrics">
      {METRICS.map((metric) => (
        <div key={metric.key}>
          <dt>{metric.label}</dt>
          <dd>{metricValue(metrics[metric.key], metric.unit)}</dd>
        </div>
      ))}
    </dl>
  )
}

function StepCard({
  step,
  active,
  onSelect,
}: {
  step: SimulationStep
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      className={`simulation-step${active ? ' simulation-step-active' : ''}`}
      aria-pressed={active}
      onClick={onSelect}
    >
      <span className="simulation-step-horizon">
        {step.horizon_months ? `+${step.horizon_months} months` : 'Present'}
      </span>
      <strong>{step.label}</strong>
      <span className={`rotation-tag ${step.status === 'COMPLETED' ? 'tag-good' : 'tag-warn'}`}>
        {step.status.replace(/_/g, ' ')}
      </span>
      <small>
        {step.as_of_date
          ? formatDate(step.as_of_date)
          : step.horizon_months
            ? 'Not anchored — no approved regional calendar'
            : 'Stored observation window'}
      </small>
    </button>
  )
}

export function SimulationPage() {
  const [farmId, setFarmId] = useState<number | null>(null)
  const [mode, setMode] = useState<ScenarioMode>('HOT_SCENARIO')
  const [windowDays, setWindowDays] = useState(30)
  const [delta, setDelta] = useState('2.00')
  const [multiplier, setMultiplier] = useState('0.70')
  const [result, setResult] = useState<SimulationRun | null>(null)
  const [activeStep, setActiveStep] = useState(0)

  const farmsQuery = useQuery({ queryKey: ['farms'], queryFn: listFarms })
  const historyQuery = useQuery({
    queryKey: ['simulations', farmId],
    queryFn: () => listSimulations(farmId as number),
    enabled: farmId !== null,
  })
  const mutation = useMutation({
    mutationFn: (payload: CreateSimulationPayload) => createSimulation(farmId as number, payload),
    onSuccess: (run) => {
      setResult(run)
      setActiveStep(0)
      void historyQuery.refetch()
    },
  })

  const selectedFarm = farmsQuery.data?.results.find((farm) => farm.id === farmId) ?? null
  const customIsEmpty = mode === 'CUSTOM' && !delta.trim() && !multiplier.trim()
  const activeStepData = result?.steps[activeStep] ?? result?.steps[0] ?? null

  function submit() {
    if (farmId === null) return
    const payload: CreateSimulationPayload = { scenario_mode: mode, window_days: windowDays }
    if (mode === 'CUSTOM') {
      if (delta.trim()) payload.temperature_delta_c = delta.trim()
      if (multiplier.trim()) payload.rainfall_multiplier = multiplier.trim()
    }
    mutation.mutate(payload)
  }

  if (farmsQuery.isPending) {
    return (
      <div className="page">
        <p className="page-loading" role="status">
          Loading your farms…
        </p>
      </div>
    )
  }
  if (farmsQuery.isError) {
    return (
      <div className="page">
        <Banner tone="error" title="Could not load farms">
          {displayError(farmsQuery.error)}{' '}
          <button className="link-button" onClick={() => void farmsQuery.refetch()}>
            Try again
          </button>
        </Banner>
      </div>
    )
  }
  if (!farmsQuery.data.results.length) {
    return (
      <div className="page">
        <header className="page-header">
          <div>
            <p className="step-kicker">Scenario lab</p>
            <h1 className="page-title">Test a what-if, honestly</h1>
          </div>
        </header>
        <section className="rotation-empty">
          <span className="rotation-icon" aria-hidden="true">↗</span>
          <h2>Start with a farm</h2>
          <p>
            Scenario simulation applies a declared assumption to environmental observations that
            are already stored for a farm. Add a farm and run a NASA POWER scan first.
          </p>
          <Link className="button button-primary" to="/onboarding">Add a farm</Link>
        </section>
      </div>
    )
  }

  return (
    <div className="page rotation-workspace simulation-workspace">
      <header className="rotation-hero">
        <div>
          <p className="step-kicker">Overfield · scenario lab</p>
          <h1 className="page-title">What changes if the scenario changes?</h1>
          <p className="page-lead">
            Apply a bounded, user-declared assumption to stored NASA POWER observations and read
            the recorded difference. Nothing here is a forecast, a measurement or a crop outcome.
          </p>
        </div>
        <div className="rotation-hero-note">
          <span aria-hidden="true">◇</span>
          <div>
            <strong>Hypothetical by design</strong>
            <small>Adjustments are assumptions. Missing evidence stays missing.</small>
          </div>
        </div>
      </header>

      <section className="rotation-controls simulation-controls" aria-label="Scenario inputs">
        <label className="field" htmlFor="simulation-farm">
          <span className="field-label">Farm</span>
          <select
            id="simulation-farm"
            className="input"
            value={farmId ?? ''}
            onChange={(event) => {
              setFarmId(event.target.value ? Number(event.target.value) : null)
              setResult(null)
            }}
          >
            <option value="">Choose a farm</option>
            {farmsQuery.data.results.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.name} · {farm.region_code || 'No region'}
              </option>
            ))}
          </select>
        </label>

        <label className="field" htmlFor="simulation-mode">
          <span className="field-label">Scenario</span>
          <select
            id="simulation-mode"
            className="input"
            value={mode}
            onChange={(event) => setMode(event.target.value as ScenarioMode)}
          >
            {MODE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field" htmlFor="simulation-window">
          <span className="field-label">Stored window (days)</span>
          <input
            id="simulation-window"
            className="input"
            type="number"
            min={1}
            max={366}
            value={windowDays}
            onChange={(event) => setWindowDays(Number(event.target.value))}
          />
        </label>

        {mode === 'CUSTOM' ? (
          <>
            <label className="field" htmlFor="simulation-delta">
              <span className="field-label">Temperature delta (°C)</span>
              <input
                id="simulation-delta"
                className="input"
                type="number"
                step="0.25"
                min={-5}
                max={5}
                value={delta}
                onChange={(event) => setDelta(event.target.value)}
              />
            </label>
            <label className="field" htmlFor="simulation-multiplier">
              <span className="field-label">Rainfall multiplier</span>
              <input
                id="simulation-multiplier"
                className="input"
                type="number"
                step="0.05"
                min={0.2}
                max={2}
                value={multiplier}
                onChange={(event) => setMultiplier(event.target.value)}
              />
            </label>
          </>
        ) : null}

        <button
          type="button"
          className="button button-primary rotation-generate"
          disabled={farmId === null || mutation.isPending || customIsEmpty}
          onClick={submit}
        >
          {mutation.isPending ? 'Applying assumption…' : 'Run hypothetical scenario'}
        </button>
      </section>

      <p className="rotation-muted">
        {MODE_OPTIONS.find((option) => option.value === mode)?.hint}
        {selectedFarm ? ` Window ends at this farm's latest stored observation, not at today.` : ''}
      </p>

      {!farmId ? (
        <Banner tone="info" title="Choose a farm to begin">
          The scenario is applied to environmental observations already stored for that farm.
        </Banner>
      ) : null}

      {mutation.isError ? (
        <Banner tone="error" title="Could not run this scenario">
          {displayError(mutation.error)}{' '}
          <button className="link-button" onClick={submit}>Try again</button>
        </Banner>
      ) : null}

      {mutation.isPending ? (
        <div className="rotation-loading" role="status">
          <span className="rotation-spinner" />
          Applying the declared adjustment to stored observations…
        </div>
      ) : null}

      {result ? (
        <>
          <section className="rotation-panel simulation-result-head" aria-live="polite">
            <div className="rotation-section-head">
              <div>
                <p className="step-kicker">Stored, reproducible run</p>
                <h2>{result.scenario.label}</h2>
              </div>
              <div className="simulation-badges">
                <span className="rotation-tag tag-warn">Hypothetical</span>
                <span
                  className={`rotation-tag ${
                    result.status === 'COMPLETED' ? 'tag-good' : 'tag-warn'
                  }`}
                >
                  {result.status.replace(/_/g, ' ')}
                </span>
                <span className="rotation-tag tag-neutral">Not ranked</span>
              </div>
            </div>
            <p className="rotation-muted">{result.hypothetical_notice}</p>
            <div className="rotation-result-meta">
              <span>Engine {result.engine_version}</span>
              <span>Crop outcomes: {result.crop_level_outcomes.replace(/_/g, ' ')}</span>
              <span>Generated {formatDate(result.created_at)}</span>
            </div>
          </section>

          {result.status === 'INSUFFICIENT_EVIDENCE' ? (
            <Banner tone="warning" title="No usable stored observations for this farm">
              The scenario was stored, but nothing can be computed. Missing evidence is reported
              below — no value is invented.{' '}
              <Link className="link-button" to={`/farms/${result.farm_id}`}>
                Open the farm to run a NASA POWER scan
              </Link>
            </Banner>
          ) : null}

          <div className="rotation-context-grid">
            <section className="rotation-panel">
              <div className="rotation-section-head">
                <div>
                  <p className="step-kicker">01 · Baseline evidence</p>
                  <h2>Stored observation window</h2>
                </div>
                <span
                  className={`rotation-tag ${
                    result.baseline.period.freshness === 'STALE' ? 'tag-warn' : 'tag-good'
                  }`}
                >
                  {freshnessLabel(result.baseline.period.freshness)}
                </span>
              </div>
              <p className="rotation-muted">
                {result.baseline.period.start && result.baseline.period.end
                  ? `${formatDate(result.baseline.period.start)} – ${formatDate(result.baseline.period.end)}`
                  : 'No observation window stored'}
                {result.baseline.period.latest_observation
                  ? ` · latest observation ${formatDate(result.baseline.period.latest_observation)}`
                  : ''}
                {` · ${result.baseline.period.days_expected} days expected`}
              </p>
              {result.baseline.metrics ? (
                <MetricGrid metrics={result.baseline.metrics} />
              ) : (
                <div className="rotation-subtle-empty">
                  <strong>No environmental metrics available</strong>
                  <p>No usable NASA POWER values are stored for this window.</p>
                </div>
              )}
              {Object.keys(result.baseline.parameters).length ? (
                <ul className="rotation-list simulation-parameters">
                  {Object.entries(result.baseline.parameters).map(([code, availability]) => (
                    <li key={code}>
                      <strong>{code}</strong>
                      <span>
                        {availability.available_days} of {result.baseline.period.days_expected}{' '}
                        days · {availability.units || 'unit not specified'}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {result.baseline.missing_inputs.length ? (
                <div className="rotation-inline-gap">
                  <strong>Missing baseline inputs</strong>
                  <ul>
                    {result.baseline.missing_inputs.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>

            <section className="rotation-panel">
              <div>
                <p className="step-kicker">02 · Recorded difference</p>
                <h2>What the assumption changes</h2>
              </div>
              {result.scenario.mode === 'BASELINE' || !Object.keys(result.differences).length ? (
                <div className="rotation-subtle-empty">
                  <strong>No adjustment applied</strong>
                  <p>
                    This run reproduces the stored observations. Choose a hot, dry or custom
                    scenario to see an explainable difference.
                  </p>
                </div>
              ) : (
                <div className="simulation-diff-table" role="table" aria-label="Scenario differences">
                  <div className="simulation-diff-row simulation-diff-header" role="row">
                    <span role="columnheader">Metric</span>
                    <span role="columnheader">Recorded</span>
                    <span role="columnheader">Scenario</span>
                    <span role="columnheader">Change</span>
                  </div>
                  {METRICS.filter((metric) => metric.key in result.differences).map((metric) => {
                    const diff = result.differences[metric.key]
                    return (
                      <div className="simulation-diff-row" role="row" key={metric.key}>
                        <span role="cell">{metric.label}</span>
                        <span role="cell">{metricValue(diff.baseline, metric.unit)}</span>
                        <span role="cell">{metricValue(diff.scenario, metric.unit)}</span>
                        <span role="cell">
                          {diff.change === null || diff.change === undefined
                            ? 'Not available'
                            : `${diff.change}${metric.unit ? ` ${metric.unit}` : ''}`}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
              <p className="rotation-muted">{result.comparison.method}</p>
            </section>
          </div>

          <section className="rotation-panel">
            <div className="rotation-section-head">
              <div>
                <p className="step-kicker">03 · Horizon checkpoints</p>
                <h2>Where the evidence is reused</h2>
              </div>
              <span className="rotation-count">No future dates asserted</span>
            </div>
            <div className="simulation-steps">
              {result.steps.map((step, index) => (
                <StepCard
                  key={step.checkpoint}
                  step={step}
                  active={index === activeStep}
                  onSelect={() => setActiveStep(index)}
                />
              ))}
            </div>
            {activeStepData ? (
              <div className="simulation-step-detail">
                <div className="rotation-section-head">
                  <div>
                    <p className="step-kicker">{activeStepData.label}</p>
                    <h3>Assumption applied to the same stored evidence</h3>
                  </div>
                  <span className="rotation-tag tag-neutral">
                    {activeStepData.horizon_months
                      ? `+${activeStepData.horizon_months} months`
                      : 'Present'}
                  </span>
                </div>
                <p className="rotation-muted">
                  Temperature delta {activeStepData.applied_adjustments.temperature_delta_c} °C ·
                  rainfall ×{activeStepData.applied_adjustments.rainfall_multiplier}
                </p>
                <MetricGrid metrics={activeStepData.metrics} />
                <div className="rotation-evidence-grid">
                  <div>
                    <h4>Assumptions</h4>
                    <ul className="rotation-list">
                      {activeStepData.assumptions.map((assumption) => (
                        <li key={assumption}>{assumption}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4>Limitations</h4>
                    <ul className="rotation-list">
                      {activeStepData.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  </div>
                </div>
                {activeStepData.missing_inputs.length ? (
                  <div className="rotation-inline-gap">
                    <strong>Missing inputs for this step</strong>
                    <ul>
                      {activeStepData.missing_inputs.map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>

          <div className="rotation-evidence-grid">
            <section className="rotation-panel">
              <h3>Limitations</h3>
              <ul className="rotation-list">
                {result.limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            </section>
            <section className="rotation-panel">
              <h3>Reproducibility and sources</h3>
              <details className="rotation-source">
                <summary>Input fingerprint</summary>
                <p>
                  <code>{result.input_sha256}</code>
                </p>
                <p>Engine version {result.engine_version}</p>
                <p>
                  Same inputs and engine version reproduce this run. The fingerprint covers the
                  stored values and the declared scenario, not the output.
                </p>
              </details>
              {result.baseline.sources.length ? (
                <details className="rotation-source">
                  <summary>NASA POWER source metadata</summary>
                  <dl className="rotation-definition-list">
                    {result.baseline.sources.map((source) => (
                      <div key={`${source.provider}-${source.parameter}`}>
                        <dt>{source.parameter}</dt>
                        <dd>
                          {source.product} · {source.units} ·{' '}
                          {source.data_category.replace(/_/g, ' ').toLowerCase()}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </details>
              ) : null}
            </section>
          </div>

          {historyQuery.data?.count ? (
            <section className="rotation-panel">
              <div className="rotation-section-head">
                <div>
                  <p className="step-kicker">Recent runs</p>
                  <h3>Stored scenarios for this farm</h3>
                </div>
                <span className="rotation-count">{historyQuery.data.count} stored</span>
              </div>
              <ul className="rotation-crop-list">
                {historyQuery.data.results.map((run) => (
                  <li key={run.simulation_id}>
                    <div>
                      <strong>{run.scenario.label}</strong>
                      <small>
                        {formatDate(run.created_at)} · {run.status.replace(/_/g, ' ')}
                      </small>
                    </div>
                    <button
                      type="button"
                      className="button button-ghost"
                      onClick={() => {
                        setResult(run)
                        setActiveStep(0)
                      }}
                    >
                      Open run
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  )
}
