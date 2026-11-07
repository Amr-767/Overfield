import { afterEach, describe, expect, it, vi } from 'vitest'

import { apiGet, getApiBaseUrl } from './client'
import { fetchHealth } from './health'
import { ApiError } from './types'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('getApiBaseUrl', () => {
  it('falls back to the documented default when the env var is unset', () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    expect(getApiBaseUrl()).toBe(DEFAULT_API_BASE_URL)
  })

  it('uses the configured value and trims trailing slashes', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://api.example.test:9000///')
    expect(getApiBaseUrl()).toBe('http://api.example.test:9000')
  })
})

describe('fetchHealth', () => {
  it('calls /api/v1/health/ and parses a healthy payload', async () => {
    vi.stubEnv('VITE_API_BASE_URL', DEFAULT_API_BASE_URL)
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        status: 'healthy',
        database: 'connected',
        timestamp: '2026-11-05T00:00:00Z',
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const health = await fetchHealth()

    expect(health.status).toBe('healthy')
    expect(health.database).toBe('connected')
    expect(fetchMock).toHaveBeenCalledWith(
      `${DEFAULT_API_BASE_URL}/api/v1/health/`,
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('surfaces a reachable-but-unhealthy 503 payload instead of treating it as unreachable', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(
        jsonResponse(
          { status: 'unhealthy', database: 'unavailable', timestamp: '2026-11-05T00:00:00Z' },
          503,
        ),
      )
    vi.stubGlobal('fetch', fetchMock)

    const health = await fetchHealth()
    expect(health.status).toBe('unhealthy')
    expect(health.database).toBe('unavailable')
  })

  it('throws ApiError when the response is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response('<html>proxy error</html>', {
            status: 200,
            headers: { 'Content-Type': 'text/html' },
          }),
        ),
    )

    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError)
  })

  it('throws ApiError on a network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed to fetch')))
    await expect(fetchHealth()).rejects.toBeInstanceOf(ApiError)
  })
})

describe('apiGet', () => {
  it('prefixes the configured base URL and parses JSON', async () => {
    vi.stubEnv('VITE_API_BASE_URL', DEFAULT_API_BASE_URL)
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const data = await apiGet<{ ok: boolean }>('/api/v1/health/')

    expect(data.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      `${DEFAULT_API_BASE_URL}/api/v1/health/`,
      expect.objectContaining({ method: 'GET' }),
    )
  })
})
