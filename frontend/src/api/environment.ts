import { apiRequest } from './client'
import { ApiError } from './types'

/**
 * Environmental data contract (Phases 3E and 4D).
 *
 * Every field mirrors the Django serializers in `apps/earth_data` and
 * `apps/indicators`. Missing values stay `null`; the UI must never turn them
 * into zero. No 0–100 score exists on this contract (`score` is always null).
 */

export type IndicatorStatusCode =
  | 'OK'
  | 'PARTIAL'
  | 'INSUFFICIENT_DATA'
  | 'NOT_ASSESSED'
  | 'UNAVAILABLE'

export type ConfidenceLevel = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH'

export type FreshnessStatus = 'FRESH' | 'RECENT' | 'STALE' | 'UNKNOWN' | 'AGEING' | 'FUTURE'

export interface MeasurementValue {
  name: string
  value: string | number | null
  unit: string
  source: string | null
  parameter: string | null
  product: string | null
  quality: string
  method: string
  interpretation: string | null
}

export interface Coverage {
  days_expected: number
  days_covered: number
  days_missing: number
  ratio: string
  by_parameter?: Record<string, number>
}

export interface Completeness {
  properties_expected: number
  properties_present: number
  ratio: string
}

export interface IndicatorPeriod {
  start: string
  end: string
  latest_observation: string | null
  age_days: number | null
  freshness: FreshnessStatus
}

export interface SourceReference {
  provider: string
  parameter: string
  units: string
  product: string
  data_category: string
  native_resolution_note: string | null
  time_standard: string
  access_date: string | null
}

export interface MissingInput {
  name: string
  impact: string
  required_for: string | null
}

export interface IndicatorDriver {
  name: string
  direction: 'POSITIVE' | 'NEGATIVE' | 'NEUTRAL'
  value: string | number | null
  unit: string | null
}

export interface Methodology {
  id: string
  version: string
  description: string
  threshold_source: string
}

export interface EnvironmentIndicator {
  code: 'WATER' | 'HEAT' | 'SOIL' | 'MARKET'
  label: string
  status: IndicatorStatusCode
  score: null
  confidence: ConfidenceLevel
  as_of: string | null
  period: IndicatorPeriod | null
  coverage: Coverage | null
  completeness: Completeness | null
  summary: string
  measurements: MeasurementValue[]
  context: MeasurementValue[]
  drivers: IndicatorDriver[]
  missing: MissingInput[]
  methodology: Methodology
  sources: SourceReference[]
  limitations: string[]
}

export interface EnvironmentWindow {
  start: string
  end: string
  days: number
  latest_observation: string | null
  age_days: number | null
  freshness: FreshnessStatus
}

export interface EnvironmentSummary {
  farm_id: number
  generated_at: string
  window: EnvironmentWindow
  data_status: IndicatorStatusCode
  freshness: {
    latest_observation: string | null
    age_days: number | null
    status: FreshnessStatus
  }
  indicators: {
    water: EnvironmentIndicator
    heat: EnvironmentIndicator
    soil: EnvironmentIndicator
    market: EnvironmentIndicator
  }
  limitations: string[]
}

export type ScanJobStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'SUCCEEDED'
  | 'PARTIALLY_SUCCEEDED'
  | 'FAILED'

export interface DataJob {
  job_id: string
  farm_id: number
  provider: string
  status: ScanJobStatus
  requested_start: string
  requested_end: string
  parameters: string[]
  days_requested: number
  days_stored: number | null
  days_missing: number | null
  error_code: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  duration_ms: number | null
  status_url: string
}

export interface ScanRequest {
  start?: string
  end?: string
  parameters?: string[]
  /** Re-fetch days that already have stored observations. */
  force?: boolean
}

export interface ScanQueuedResponse {
  status: 'QUEUED'
  farm_id: number
  job_id: string
  task_id: string
  start: string
  end: string
  parameters: string[]
  status_url: string
}

export interface ScanCurrentResponse {
  status: 'already_current'
  farm_id: number
  start: string
  end: string
  parameters: string[]
  detail: string
}

export interface ScanRunningResponse {
  status: 'already_running'
  farm_id: number
  job_id: string
  detail: string
  status_url: string
}

/** A scan POST either queues a job or reports that stored data is current. */
export type ScanResponse = ScanQueuedResponse | ScanCurrentResponse

export const DEFAULT_WINDOW_DAYS = 30
export const WINDOW_DAY_OPTIONS = [7, 14, 30, 90, 180, 365] as const

function summaryPath(farmId: number, windowDays: number): string {
  return `/api/v1/farms/${farmId}/environment/current/?window_days=${windowDays}`
}

/** Current four-indicator summary. The window ends at the latest observation. */
export function getEnvironmentSummary(
  farmId: number,
  windowDays: number = DEFAULT_WINDOW_DAYS,
  signal?: AbortSignal,
): Promise<EnvironmentSummary> {
  return apiRequest<EnvironmentSummary>(summaryPath(farmId, windowDays), {
    auth: true,
    signal,
  })
}

/**
 * Queue a NASA POWER scan. The 202 body is returned as `ScanQueuedResponse`.
 * A 200 `already_current` body is returned as `ScanCurrentResponse`; a 409
 * `already_running` response is thrown as an `ApiError` whose `payload`
 * carries the running job id.
 */
export function requestScan(
  farmId: number,
  payload: ScanRequest = {},
  signal?: AbortSignal,
): Promise<ScanResponse> {
  return apiRequest<ScanResponse>(`/api/v1/farms/${farmId}/scans/`, {
    method: 'POST',
    body: payload,
    auth: true,
    signal,
  })
}

/** Status of one fetch job. Poll only while PENDING/RUNNING. */
export function getDataJob(jobId: string, signal?: AbortSignal): Promise<DataJob> {
  return apiRequest<DataJob>(`/api/v1/data-jobs/${jobId}/`, { auth: true, signal })
}

/**
 * Read the job handle from a documented error body (409 already_running or
 * 503 broker-unavailable). Returns null when the payload has no job id.
 */
export function jobIdFromError(error: unknown): string | null {
  if (!(error instanceof ApiError)) return null
  const payload = error.payload
  if (!payload || typeof payload !== 'object' || !('job_id' in payload)) {
    return null
  }
  const jobId = (payload as { job_id?: unknown }).job_id
  return typeof jobId === 'string' ? jobId : null
}
