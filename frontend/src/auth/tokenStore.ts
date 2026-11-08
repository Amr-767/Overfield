/**
 * Refresh-token persistence.
 *
 * The access token is kept in memory only (ADR-009). The refresh token is kept
 * in `sessionStorage` so a page reload inside the same tab can restore the
 * session without keeping a long-lived credential in `localStorage`.
 */

const REFRESH_TOKEN_KEY = 'agrospace.refresh-token'

export function loadRefreshToken(): string | null {
  try {
    return window.sessionStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function saveRefreshToken(token: string): void {
  try {
    window.sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
  } catch {
    // Storage can be unavailable (private mode); the session then cannot survive reloads.
  }
}

export function clearRefreshToken(): void {
  try {
    window.sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  } catch {
    // Ignore: nothing to clear if storage is unavailable.
  }
}
