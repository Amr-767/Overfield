import { apiRequest } from './client'
import type {
  BoundaryGeometry,
  BoundaryValidation,
  FarmerContext,
  FarmerContextPayload,
  Farm,
  FarmCreatePayload,
  FarmZone,
  Paginated,
} from './types'

export function listFarms(): Promise<Paginated<Farm>> {
  return apiRequest<Paginated<Farm>>('/api/v1/farms/', { auth: true })
}

export function getFarm(farmId: number): Promise<Farm> {
  return apiRequest<Farm>(`/api/v1/farms/${farmId}/`, { auth: true })
}

export function createFarm(payload: FarmCreatePayload): Promise<Farm> {
  return apiRequest<Farm>('/api/v1/farms/', { method: 'POST', body: payload, auth: true })
}

export type FarmUpdatePayload = Partial<FarmCreatePayload>

export function updateFarm(farmId: number, payload: FarmUpdatePayload): Promise<Farm> {
  return apiRequest<Farm>(`/api/v1/farms/${farmId}/`, {
    method: 'PATCH',
    body: payload,
    auth: true,
  })
}

export function deleteFarm(farmId: number): Promise<void> {
  return apiRequest<void>(`/api/v1/farms/${farmId}/`, { method: 'DELETE', auth: true })
}

/** Backend-validated geometry: returns the geodesic area without saving. */
export function validateBoundary(
  boundary: BoundaryGeometry,
  signal?: AbortSignal,
): Promise<BoundaryValidation> {
  return apiRequest<BoundaryValidation>('/api/v1/farms/validate-boundary/', {
    method: 'POST',
    body: { boundary },
    auth: true,
    signal,
  })
}

export function listZones(farmId: number): Promise<Paginated<FarmZone>> {
  return apiRequest<Paginated<FarmZone>>(`/api/v1/farms/${farmId}/zones/`, { auth: true })
}

export function getFarmContext(farmId: number): Promise<FarmerContext> {
  return apiRequest<FarmerContext>(`/api/v1/farms/${farmId}/context/`, { auth: true })
}

export function saveFarmContext(
  farmId: number,
  payload: FarmerContextPayload,
  partial = true,
): Promise<FarmerContext> {
  return apiRequest<FarmerContext>(`/api/v1/farms/${farmId}/context/`, {
    method: partial ? 'PATCH' : 'PUT',
    body: payload,
    auth: true,
  })
}
