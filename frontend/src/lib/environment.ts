import type {
  ConfidenceLevel,
  FreshnessStatus,
  IndicatorStatusCode,
  MeasurementValue,
} from '../api/environment'

export type TagTone = 'good' | 'warn' | 'unknown' | 'neutral' | 'unavailable'

export function statusLabel(status: IndicatorStatusCode): string {
  switch (status) {
    case 'OK':
      return 'Available'
    case 'PARTIAL':
      return 'Partial'
    case 'INSUFFICIENT_DATA':
      return 'Insufficient data'
    case 'NOT_ASSESSED':
      return 'Not assessed'
    case 'UNAVAILABLE':
      return 'Unavailable'
  }
}

export function statusTone(status: IndicatorStatusCode): TagTone {
  switch (status) {
    case 'OK':
      return 'good'
    case 'PARTIAL':
      return 'warn'
    case 'INSUFFICIENT_DATA':
      return 'unknown'
    case 'NOT_ASSESSED':
      return 'neutral'
    case 'UNAVAILABLE':
      return 'unavailable'
  }
}

export function freshnessLabel(freshness: FreshnessStatus): string {
  switch (freshness) {
    case 'FRESH':
      return 'Fresh'
    case 'RECENT':
      return 'Recent'
    case 'STALE':
      return 'Stale'
    case 'AGEING':
      return 'Ageing sample'
    case 'FUTURE':
      return 'Future-dated'
    case 'UNKNOWN':
      return 'Unknown age'
  }
}

export function freshnessTone(freshness: FreshnessStatus): TagTone {
  switch (freshness) {
    case 'FRESH':
      return 'good'
    case 'RECENT':
      return 'neutral'
    case 'STALE':
    case 'AGEING':
    case 'FUTURE':
      return 'warn'
    case 'UNKNOWN':
      return 'unknown'
  }
}

export function confidenceLabel(confidence: ConfidenceLevel): string {
  switch (confidence) {
    case 'HIGH':
      return 'High'
    case 'MEDIUM':
      return 'Medium'
    case 'LOW':
      return 'Low'
    case 'NONE':
      return 'None'
  }
}

export function confidenceTone(confidence: ConfidenceLevel): TagTone {
  if (confidence === 'HIGH') return 'good'
  if (confidence === 'MEDIUM') return 'neutral'
  if (confidence === 'LOW') return 'warn'
  return 'unknown'
}

const MEASUREMENT_LABELS: Record<string, string> = {
  precipitation_total: 'Rainfall total',
  rainy_days: 'Rainy days',
  max_daily_rainfall: 'Maximum daily rainfall',
  longest_observed_dry_spell: 'Longest observed dry spell',
  mean_temperature: 'Mean temperature',
  mean_daily_maximum: 'Mean daily maximum',
  mean_daily_minimum: 'Mean daily minimum',
  hot_days: 'Hot days',
  very_hot_days: 'Very hot days',
  cool_nights: 'Cool nights',
  ph: 'pH',
  organic_carbon_percent: 'Organic carbon',
  nitrogen_ppm: 'Nitrogen',
  phosphorus_ppm: 'Phosphorus',
  potassium_ppm: 'Potassium',
  texture_class: 'Texture class',
  sample_date: 'Sample date',
  sampling_depth_cm: 'Sampling depth',
  sampling_method: 'Sampling / extraction method',
  lab_name: 'Laboratory',
  irrigation_available: 'Irrigation available',
  irrigation_type: 'Irrigation method',
  water_reliability: 'Reported water reliability',
}

/** Readable label for a backend measurement name; unknown names stay readable. */
export function measurementLabel(name: string): string {
  return MEASUREMENT_LABELS[name] ?? name.replace(/_/g, ' ')
}

function trimNumeric(value: string): string {
  if (!/^-?\d+(\.\d+)?$/.test(value)) return value
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return value
  return String(Number(numeric.toFixed(4)))
}

/**
 * Render a measurement without inventing values: null stays "Not available",
 * and units are shown exactly as the API reports them.
 */
export function measurementText(measurement: MeasurementValue): string {
  const { value, unit } = measurement
  if (value === null || value === '') return 'Not available'
  const raw = typeof value === 'number' ? String(value) : trimNumeric(value)

  if (unit === 'boolean') {
    if (raw === 'yes' || raw === 'true') return 'Yes'
    if (raw === 'no' || raw === 'false') return 'No'
    return raw
  }
  if (unit === 'class' || unit === 'text') return raw.replace(/_/g, ' ')
  if (unit === 'date') return raw
  if (unit === 'pH') return `${raw} pH`
  if (!unit) return raw
  return `${raw} ${unit}`
}

/** True when the backend reported a numeric coverage ratio that is safe to state. */
export function coverageText(daysCovered: number, daysExpected: number, daysMissing: number): string {
  const base = `${daysCovered} of ${daysExpected} days observed`
  return daysMissing > 0 ? `${base} · ${daysMissing} missing` : base
}

export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return 'Not recorded'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  })
}
