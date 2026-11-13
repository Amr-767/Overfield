import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { apiRequest, setAccessToken, setUnauthorizedHandler } from './client'
import { ApiError } from './types'

const BASE = 'http://127.0.0.1:8000'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

beforeEach(() => {
  vi.stubEnv('VITE_API_BASE_URL', BASE)
  setAccessToken(null)
  setUnauthorizedHandler(null)
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  setUnauthorizedHandler(null)
  setAccessToken(null)
})

describe('apiRequest', () => {
  it('sends JSON and parses the response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    const data = await apiRequest<{ id: number }>('/api/v1/farms/', {
      method: 'POST',
      body: { name: 'Field' },
    })

    expect(data.id).toBe(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe(`${BASE}/api/v1/farms/`)
    expect(init.method).toBe('POST')
    expect(init.body).toBe(JSON.stringify({ name: 'Field' }))
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(init.headers.Authorization).toBeUndefined()
  })

  it('attaches the bearer token for authenticated requests', async () => {
    setAccessToken('test-access-token')
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ count: 0, results: [] }))
    vi.stubGlobal('fetch', fetchMock)

    await apiRequest('/api/v1/farms/', { auth: true })

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer test-access-token')
  })

  it('maps Django field errors into ApiError.fieldMessages', async () => {
    // A fresh Response per call: bodies can only be read once.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(async () =>
        jsonResponse(
          {
            boundary: ['Invalid polygon: geometry is not closed.'],
            name: ['This field is required.'],
          },
          400,
        ),
      ),
    )

    await expect(
      apiRequest('/api/v1/farms/', { method: 'POST', body: {}, auth: true }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      fieldErrors: {
        boundary: ['Invalid polygon: geometry is not closed.'],
      },
    })

    try {
      await apiRequest('/api/v1/farms/', { method: 'POST', body: {}, auth: true })
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError)
      expect((error as ApiError).fieldMessages.boundary).toMatch(/not closed/)
      expect((error as ApiError).fieldMessages.name).toBe('This field is required.')
    }
  })

  it('uses `detail` as the message for authentication failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'Invalid token.' }, 401)))

    await expect(apiRequest('/api/v1/me/', { auth: true })).rejects.toMatchObject({
      message: 'Invalid token.',
      status: 401,
    })
  })

  it('refreshes once and retries when the access token expired', async () => {
    const onUnauthorized = vi.fn().mockResolvedValue(true)
    setUnauthorizedHandler(onUnauthorized)
    setAccessToken('expired')

    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ detail: 'expired' }, 401))
      .mockResolvedValueOnce(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiRequest<{ ok: boolean }>('/api/v1/me/', { auth: true })

    expect(result.ok).toBe(true)
    expect(onUnauthorized).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('does not retry when the refresh handler fails', async () => {
    setUnauthorizedHandler(vi.fn().mockResolvedValue(false))
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ detail: 'expired' }, 401))
    vi.stubGlobal('fetch', fetchMock)

    await expect(apiRequest('/api/v1/me/', { auth: true })).rejects.toMatchObject({ status: 401 })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('returns undefined for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(apiRequest('/api/v1/farms/1/', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('reports an unreachable API clearly', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('failed to fetch')))

    await expect(apiRequest('/api/v1/farms/')).rejects.toMatchObject({
      message: expect.stringContaining('Cannot reach the Overfield API'),
    })
  })
})
