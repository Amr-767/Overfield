/** Shared API and domain types for the Overfield SPA. */

/** Response shape for GET /api/v1/health/ (Phase 1B contract). */
export interface HealthResponse {
  status: string
  database: string
  timestamp: string
  /** Optional; omitted until a later readiness field is added. */
  postgis?: string
}

export interface ApiFieldErrors {
  [field: string]: string[]
}

export class ApiError extends Error {
  readonly status?: number
  readonly fieldErrors?: ApiFieldErrors
  /**
   * Parsed JSON error body when the endpoint returns structured detail
   * (for example the scan API's 409 `already_running` job handle).
   */
  readonly payload?: unknown

  constructor(
    message: string,
    status?: number,
    fieldErrors?: ApiFieldErrors,
    payload?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
    this.payload = payload
  }

  /** First error message per field, useful for inline form messages. */
  get fieldMessages(): Record<string, string> {
    const messages: Record<string, string> = {}
    for (const [field, errors] of Object.entries(this.fieldErrors ?? {})) {
      if (errors.length > 0) {
        messages[field] = errors[0]
      }
    }
    return messages
  }
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// --- GeoJSON -------------------------------------------------------------

export type Position = [number, number]

export interface PointGeometry {
  type: 'Point'
  coordinates: Position
}

export interface PolygonGeometry {
  type: 'Polygon'
  coordinates: Position[][] | number[][][]
}

export interface MultiPolygonGeometry {
  type: 'MultiPolygon'
  coordinates: number[][][][]
}

export type BoundaryGeometry = PolygonGeometry | MultiPolygonGeometry

// --- Accounts ------------------------------------------------------------

export interface Profile {
  username: string
  display_name: string
  email: string
  preferred_language: string
  created_at?: string
  updated_at?: string
}

export interface RegisterPayload {
  username: string
  password: string
  email?: string
  display_name?: string
  preferred_language?: string
}

export interface TokenPair {
  access: string
  refresh: string
}

// --- Farms ---------------------------------------------------------------

export type AreaSource = 'GEOMETRY_DERIVED' | 'FARMER_REPORTED'
export type GeometrySource = 'BOUNDARY' | 'LOCATION_POINT'
export type SpatialPrecision = 'HIGH' | 'LOW'

export interface Farm {
  id: number
  name: string
  country_code: string
  region_code: string
  boundary: MultiPolygonGeometry | null
  location: PointGeometry | null
  area_hectares: string
  area_source: AreaSource
  geometry_source: GeometrySource
  spatial_precision: SpatialPrecision
  timezone: string
  zone_count: number
  created_at: string
  updated_at: string
}

export interface FarmCreatePayload {
  name: string
  country_code?: string
  region_code?: string
  timezone?: string
  boundary?: BoundaryGeometry
  location?: PointGeometry
  farmer_reported_area_hectares?: string
}

export interface BoundaryValidation {
  valid: boolean
  srid: number
  area_hectares: string
  area_method: string
  geometry: MultiPolygonGeometry
}

export interface FarmZone {
  id: number
  farm: number
  name: string
  boundary: MultiPolygonGeometry
  area_hectares: string
  notes: string
  created_at: string
}

export type Provenance =
  | 'FARMER_REPORTED'
  | 'LAB_TEST'
  | 'EXTERNAL_PROVIDER'
  | 'REMOTE_SENSING'
  | 'UNKNOWN'

export interface CropEntry {
  id?: number
  season: string
  crop: string
  crop_code?: string
  source?: Provenance
  notes?: string
}

export interface FarmerConstraints {
  equipment?: string[]
  seed_availability?: string
  labor_availability?: string
}

export interface FarmerContext {
  farm_id: number
  soil_source: Provenance
  texture_class: string
  ph: string | null
  organic_carbon_percent: string | null
  nitrogen_ppm: string | null
  phosphorus_ppm: string | null
  potassium_ppm: string | null
  sampling_depth_cm: number | null
  sampling_method: string
  lab_name: string
  sample_date: string | null
  water_source: Provenance
  irrigation_available: boolean | null
  irrigation_type: string
  water_reliability: string
  priorities: Record<string, number>
  constraints: FarmerConstraints
  current_crops: CropEntry[]
  created_at: string
  updated_at: string
}

export type FarmerContextPayload = Partial<Omit<FarmerContext, 'farm_id' | 'created_at' | 'updated_at'>>
