import { ApiError, type ApiFieldErrors } from './types'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export interface ApiRequestOptions {
  method?: HttpMethod
  body?: unknown
  /** Attach the in-memory access token and retry once after a refresh. */
  auth?: boolean
  signal?: AbortSignal
}

let accessToken: string | null = null
let unauthorizedHandler: (() => Promise<boolean>) | null = null

/** The access token lives in memory only (ADR-009). */
export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

/**
 * Registered by the auth provider so an expired access token can be refreshed
 * transparently. Returns true when a new access token was obtained.
 */
export function setUnauthorizedHandler(handler: (() => Promise<boolean>) | null): void {
  unauthorizedHandler = handler
}

/**
 * Public API base URL only. Never put secrets, DB passwords, or NASA
 * credentials in Vite env vars — they are embedded in the browser bundle.
 */
export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim()
  return (configured || DEFAULT_API_BASE_URL).replace(/\/+$/, '')
}

function buildUrl(path: string): string {
  return `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`
}

function extractFieldErrors(payload: unknown): ApiFieldErrors | undefined {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return undefined
  }
  const fields: ApiFieldErrors = {}
  for (const [key, value] of Object.entries(payload as Record<string, unknown>)) {
    if (key === 'detail' || key === 'code') {
      continue
    }
    const messages = Array.isArray(value) ? value.map(String) : [String(value)]
    if (messages.length > 0) {
      fields[key] = messages
    }
  }
  return Object.keys(fields).length > 0 ? fields : undefined
}

async function parseError(response: Response): Promise<ApiError> {
  const contentType = response.headers.get('content-type') ?? ''
  let payload: unknown = null
  if (contentType.includes('application/json')) {
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
  }

  const fieldErrors = extractFieldErrors(payload)
  let message = `Request failed with status ${response.status}`
  if (payload && typeof payload === 'object' && 'detail' in payload) {
    message = String((payload as { detail: unknown }).detail)
  } else if (fieldErrors) {
    const [firstField, firstMessages] = Object.entries(fieldErrors)[0]
    message = firstMessages?.[0] ?? `Invalid value for ${firstField}`
  } else if (response.status === 401) {
    message = 'Your session has expired. Please sign in again.'
  }

  return new ApiError(message, response.status, fieldErrors, payload)
}

async function send(
  path: string,
  options: ApiRequestOptions,
  retryOnUnauthorized: boolean,
): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (options.auth && accessToken) {
    headers.Authorization = `Bearer ${accessToken}`
  }

  let response: Response
  try {
    response = await fetch(buildUrl(path), {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch {
    throw new ApiError(
      `Cannot reach the Overfield API at ${getApiBaseUrl()}. Confirm the backend is running and VITE_API_BASE_URL is correct.`,
    )
  }

  if (response.status === 401 && options.auth && retryOnUnauthorized && unauthorizedHandler) {
    const refreshed = await unauthorizedHandler()
    if (refreshed) {
      return send(path, options, false)
    }
  }

  return response
}

/** Perform a JSON request against the Django API. */
export async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const response = await send(path, options, true)

  if (!response.ok) {
    throw await parseError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers.get('content-type') ?? ''
  if (!contentType.includes('application/json')) {
    throw new ApiError(
      `Expected a JSON response from ${path} but received ${contentType || 'an unknown content type'}.`,
      response.status,
    )
  }

  return (await response.json()) as T
}

/** Convenience wrapper kept for the Phase 1 health check and tests. */
export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  return apiRequest<T>(path, {
    method: 'GET',
    signal: init?.signal ?? undefined,
  })
}
