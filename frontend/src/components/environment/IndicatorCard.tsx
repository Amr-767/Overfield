import type { EnvironmentIndicator, MeasurementValue } from '../../api/environment'
import {
  confidenceLabel,
  confidenceTone,
  coverageText,
  freshnessLabel,
  freshnessTone,
  measurementLabel,
  measurementText,
  statusLabel,
  statusTone,
} from '../../lib/environment'

const ICONS: Record<EnvironmentIndicator['code'], string> = {
  WATER: '≋',
  HEAT: '☀',
  SOIL: '▤',
  MARKET: '◇',
}

function MeasurementList({ items, title }: { items: MeasurementValue[]; title: string }) {
  if (items.length === 0) {
    return <p className="env-unknown">{title}: none reported.</p>
  }
  return (
    <dl className="env-metrics" aria-label={title}>
      {items.map((measurement) => (
        <div key={`${measurement.name}-${measurement.parameter ?? ''}`}>
          <dt>{measurementLabel(measurement.name)}</dt>
          <dd className={measurement.value === null ? 'env-unknown' : undefined}>
            {measurementText(measurement)}
          </dd>
          {measurement.interpretation ? (
            <dd className="env-interpretation">{measurement.interpretation.replace(/_/g, ' ')}</dd>
          ) : null}
          {measurement.method ? <small className="env-method">{measurement.method}</small> : null}
        </div>
      ))}
    </dl>
  )
}

function DataProvenanceDetails({ indicator }: { indicator: EnvironmentIndicator }) {
  const hasDetails =
    indicator.sources.length > 0 ||
    indicator.limitations.length > 0 ||
    Boolean(indicator.methodology.description)

  if (!hasDetails) return null

  return (
    <details className="env-details">
      <summary>Source, method and limitations</summary>

      {indicator.sources.length > 0 ? (
        <div className="env-source-block">
          {indicator.sources.map((source) => (
            <dl
              className="env-definition-list"
              key={`${source.provider}-${source.parameter}-${source.product}`}
            >
              <div>
                <dt>Provider</dt>
                <dd>{source.provider.replace(/_/g, ' ')}</dd>
              </div>
              <div>
                <dt>Product</dt>
                <dd>{source.product || 'Not specified'}</dd>
              </div>
              <div>
                <dt>Parameter</dt>
                <dd>{source.parameter || 'Not specified'}</dd>
              </div>
              <div>
                <dt>Units</dt>
                <dd>{source.units || 'Not specified'}</dd>
              </div>
              <div>
                <dt>Data category</dt>
                <dd>{source.data_category.replace(/_/g, ' ')}</dd>
              </div>
              <div>
                <dt>Time standard</dt>
                <dd>{source.time_standard || 'Not specified'}</dd>
              </div>
              {source.native_resolution_note ? (
                <div>
                  <dt>Native resolution</dt>
                  <dd>{source.native_resolution_note}</dd>
                </div>
              ) : null}
              {source.access_date ? (
                <div>
                  <dt>Accessed</dt>
                  <dd>{source.access_date}</dd>
                </div>
              ) : null}
            </dl>
          ))}
        </div>
      ) : (
        <p className="env-unknown">No external provider is attached to this indicator.</p>
      )}

      <div className="env-method-block">
        <h4>Method</h4>
        <p>{indicator.methodology.description || 'No methodology description provided.'}</p>
        <p className="env-method">
          {indicator.methodology.id} · version {indicator.methodology.version}
        </p>
        {indicator.methodology.threshold_source ? (
          <p className="env-method">{indicator.methodology.threshold_source}</p>
        ) : null}
      </div>

      {indicator.limitations.length > 0 ? (
        <div className="env-method-block">
          <h4>Limitations</h4>
          <ul className="env-list">
            {indicator.limitations.map((limitation, index) => (
              <li key={index}>{limitation}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </details>
  )
}

export function IndicatorCard({
  indicator,
  index,
}: {
  indicator: EnvironmentIndicator
  index: number
}) {
  const confidenceTitle =
    'Coverage-based confidence, capped by the source type. It is not a field-measurement guarantee.'

  return (
    <article className={`env-card env-card-${indicator.code.toLowerCase()}`}>
      <header className="env-card-head">
        <span className="env-icon" aria-hidden="true">
          {ICONS[indicator.code]}
        </span>
        <div className="env-card-title">
          <p className="step-kicker">{String(index).padStart(2, '0')}</p>
          <h2>{indicator.label}</h2>
        </div>
        <span className={`env-tag env-tag-${statusTone(indicator.status)}`}>
          {statusLabel(indicator.status)}
        </span>
      </header>

      <p className="env-summary">{indicator.summary}</p>

      <div className="env-tags" aria-label="Indicator quality metadata">
        <span
          className={`env-tag env-tag-${confidenceTone(indicator.confidence)}`}
          title={confidenceTitle}
        >
          Confidence: {confidenceLabel(indicator.confidence)}
        </span>
        {indicator.period ? (
          <span className={`env-tag env-tag-${freshnessTone(indicator.period.freshness)}`}>
            {freshnessLabel(indicator.period.freshness)}
          </span>
        ) : (
          <span className="env-tag env-tag-unavailable">No observation period</span>
        )}
        {indicator.coverage ? (
          <span className="env-tag env-tag-neutral">
            {coverageText(
              indicator.coverage.days_covered,
              indicator.coverage.days_expected,
              indicator.coverage.days_missing,
            )}
          </span>
        ) : null}
        {indicator.completeness ? (
          <span className="env-tag env-tag-neutral">
            {indicator.completeness.properties_present} of{' '}
            {indicator.completeness.properties_expected} properties recorded
          </span>
        ) : null}
      </div>

      <MeasurementList items={indicator.measurements} title={`${indicator.label} measurements`} />

      {indicator.measurements.length === 0 ? (
        <p className="env-unknown">
          {'No measurement values are reported. This is not zero — the indicator cannot be reported with the available evidence.'}
        </p>
      ) : null}

      {indicator.context.length > 0 ? (
        <div className="env-context">
          <h3>Farmer-reported context</h3>
          <p className="env-method">
            Recorded by you; shown as context only, not used as an environmental measurement.
          </p>
          <MeasurementList items={indicator.context} title={`${indicator.label} context`} />
        </div>
      ) : null}

      {indicator.period ? (
        <p className="env-period">
          Analysed {indicator.period.start} → {indicator.period.end}
          {indicator.period.latest_observation
            ? ` · latest observation ${indicator.period.latest_observation}`
            : ''}
          {indicator.period.age_days !== null
            ? ` · ${indicator.period.age_days} day(s) old`
            : ''}
        </p>
      ) : null}

      {indicator.missing.length > 0 ? (
        <details className="env-details" open={indicator.status !== 'OK'}>
          <summary>Missing inputs ({indicator.missing.length})</summary>
          <ul className="env-list">
            {indicator.missing.map((item) => (
              <li key={`${item.name}-${item.required_for ?? ''}`}>
                <strong>{measurementLabel(item.name)}</strong>
                {item.required_for ? ` · required for ${item.required_for.replace(/_/g, ' ')}` : ''}
                <span>{item.impact}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}

      <DataProvenanceDetails indicator={indicator} />
    </article>
  )
}
