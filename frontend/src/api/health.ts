import { getApiBaseUrl } from './client'
import { ApiError, type HealthResponse } from './types'

/**
 * Fetch readiness from Django.
 * A 503 with a JSON body still means the API process is reachable; surface
 * database/status fields instead of treating it as a total connectivity failure.
 */
export async function fetchHealth(): Promise<HealthResponse> {
  const url = `${getApiBaseUrl()}/api/v1/health/`

  let response: Response
  try {
    response = await fetch(url, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    })
  } catch {
    throw new ApiError(
      `Cannot reach the Django API at ${getApiBaseUrl()}. Start the backend with python manage.py runserver and confirm VITE_API_BASE_URL.`,
    )
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new ApiError(
      `Django responded with a non-JSON health payload (HTTP ${response.status}).`,
      response.status,
    )
  }

  const payload = (await response.json()) as HealthResponse

  if (!response.ok && response.status !== 503) {
    throw new ApiError(
      `Health check failed with status ${response.status}.`,
      response.status,
    )
  }

  if (
    typeof payload?.status !== 'string' ||
    typeof payload?.database !== 'string'
  ) {
    throw new ApiError('Health response was missing required fields.')
  }

  return payload
}
