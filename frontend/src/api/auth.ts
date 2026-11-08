import { apiRequest } from './client'
import type { Profile, RegisterPayload, TokenPair } from './types'

export function registerFarmer(payload: RegisterPayload): Promise<Profile> {
  return apiRequest<Profile>('/api/v1/auth/register/', { method: 'POST', body: payload })
}

export function requestTokenPair(username: string, password: string): Promise<TokenPair> {
  return apiRequest<TokenPair>('/api/v1/auth/token/', {
    method: 'POST',
    body: { username, password },
  })
}

export function refreshAccessToken(refresh: string): Promise<{ access: string }> {
  return apiRequest<{ access: string }>('/api/v1/auth/token/refresh/', {
    method: 'POST',
    body: { refresh },
  })
}

export function fetchProfile(): Promise<Profile> {
  return apiRequest<Profile>('/api/v1/me/', { auth: true })
}

export interface ProfileUpdatePayload {
  display_name?: string
  preferred_language?: string
  email?: string
}

export function updateProfile(payload: ProfileUpdatePayload): Promise<Profile> {
  return apiRequest<Profile>('/api/v1/me/', { method: 'PATCH', body: payload, auth: true })
}
