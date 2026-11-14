import { afterEach, describe, expect, it, vi } from 'vitest'

import { getApiBaseUrl } from './client'
import {
  getDataJob,
  getEnvironmentSummary,
  jobIdFromError,
  requestScan,
} from './environment'
import { ApiError } from './types'

const BASE = 'http://127.0.0.1:8000'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('environment API client', () => {
  it('requests the summary from the documented farm-scoped path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ farm_id: 12 }))
    vi.stubGlobal('fetch', fetchMock)

    await getEnvironmentSummary(12, 30)

    expect(getApiBaseUrl()).toBe(BASE)
    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/api/v1/farms/12/environment/current/?window_days=30`,
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('posts an empty scan body by default and the force flag only when asked', async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(jsonResponse({ status: 'QUEUED', job_id: 'job-1' }, 202)),
    )
    vi.stubGlobal('fetch', fetchMock)

    await requestScan(12)
    await requestScan(12, { force: true })

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `${BASE}/api/v1/farms/12/scans/`,
      expect.objectContaining({ method: 'POST', body: JSON.stringify({}) }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `${BASE}/api/v1/farms/12/scans/`,
      expect.objectContaining({ method: 'POST', body: JSON.stringify({ force: true }) }),
    )
  })

  it('polls the documented data-job path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ job_id: 'job-1' }))
    vi.stubGlobal('fetch', fetchMock)

    await getDataJob('11111111-1111-4111-8111-111111111111')

    expect(fetchMock).toHaveBeenCalledWith(
      `${BASE}/api/v1/data-jobs/11111111-1111-4111-8111-111111111111/`,
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('keeps the running job handle from a 409 response available to the UI', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            status: 'already_running',
            farm_id: 12,
            job_id: 'job-running',
            detail: 'A scan is already running for this farm.',
            status_url: '/api/v1/data-jobs/job-running/',
          },
          409,
        ),
      ),
    )

    let caught: unknown
    try {
      await requestScan(12)
    } catch (error) {
      caught = error
    }

    expect(caught).toBeInstanceOf(ApiError)
    expect((caught as ApiError).status).toBe(409)
    expect(jobIdFromError(caught)).toBe('job-running')
  })

  it('exposes the job handle on a 503 broker failure instead of guessing success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            detail: 'The background worker is unavailable; the scan was not queued.',
            job_id: 'job-failed',
            status: 'failed',
          },
          503,
        ),
      ),
    )

    let caught: unknown
    try {
      await requestScan(12)
    } catch (error) {
      caught = error
    }

    expect((caught as ApiError).status).toBe(503)
    expect(jobIdFromError(caught)).toBe('job-failed')
  })

  it('reports a network failure as an ApiError, never as a successful scan', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed to fetch')))

    await expect(getEnvironmentSummary(12)).rejects.toBeInstanceOf(ApiError)
  })
})
