import { ApiError } from './types'

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

/**
 * Public API base URL only. Never put secrets, DB passwords, or NASA
 * credentials in Vite env vars — they are embedded in the browser bundle.
 */
export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim()
  return (configured || DEFAULT_API_BASE_URL).replace(/\/+$/, '')
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`

  let response: Response
  try {
    response = await fetch(url, {
      ...init,
      method: 'GET',
      headers: {
        Accept: 'application/json',
        ...(init?.headers ?? {}),
      },
    })
  } catch {
    throw new ApiError(
      `Cannot reach the Django API at ${getApiBaseUrl()}. Start the backend with python manage.py runserver and confirm VITE_API_BASE_URL.`,
    )
  }

  const contentType = response.headers.get('content-type') ?? ''
  const isJson = contentType.includes('application/json')
  const payload = isJson ? await response.json() : null

  if (!response.ok) {
    const detail =
      payload && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`
    throw new ApiError(detail, response.status)
  }

  return payload as T
}
