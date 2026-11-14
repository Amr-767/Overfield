import { apiRequest } from './client'
import type { FarmerContext, Farm, Paginated } from './types'

export interface CropSummary {
  id: number
  code: string
  name: string
  scientific_name: string
  crop_family: string
  source_status: string
  evidence_ids: string[]
}

export interface CropCharacteristic {
  id: number
  source_crop_identifier: string
  cultivar_or_variety: string
  characteristic_name: string
  value_type: 'NUMBER' | 'TEXT' | 'BOOLEAN'
  original_value: string | null
  original_unit: string
  normalized_value: string | null
  normalized_text?: string | null
  normalized_boolean?: boolean | null
  normalized_unit: string
  temporal_applicability: string
  geographic_scope: string
  geographic_applicability: string
  source_record_identifier: string
  source_record_url: string | null
  evidence_reference: string | null
  validation_status: string
  source: {
    dataset_identifier: string
    publisher: string
    dataset_version: string | null
    doi: string | null
    license: string | null
    attribution: string | null
    landing_page_url: string | null
    resource_identifier?: string | null
    resource_url?: string | null
  }
}

export interface CropProfile extends CropSummary {
  characteristics: CropCharacteristic[]
  missing_characteristics: string[]
}

export interface CropCalendarSeason {
  season_code: string
  label: string
  start_month_day: string
  end_month_day: string
  evidence_ids: string[]
  crops: Array<{
    crop_code: string
    planting_window: string | null
    harvest_window: string | null
    evidence_ids: string[]
  }>
}

export interface CropCalendar {
  region_code: string
  country_code: string
  timezone: string
  calendar_version: string
  source: {
    title: string | null
    publisher: string | null
    url: string | null
    evidence_reference: string | null
  }
  seasons: CropCalendarSeason[]
}

export interface EnvironmentCurrent {
  farm_id: number
  generated_at: string
  window: {
    start: string
    end: string
    days: number
    latest_observation: string | null
    age_days: number | null
    freshness: 'FRESH' | 'RECENT' | 'STALE' | 'UNKNOWN'
  }
  data_status: string
  indicators: Record<string, {
    code: string
    status: string
    score: number | null
    confidence: string
    as_of: string | null
    summary: string
    missing: Array<{ name: string; impact?: string; required_for?: string }>
    sources: Array<{ provider: string; parameter: string; units: string; product: string; native_resolution_note?: string | null }>
    limitations: string[]
  }>
  limitations: string[]
}

export interface RotationSeason {
  season_code: string | null
  start_date?: string
  end_date?: string
  crop_code: string | null
  crop_name?: string | null
  source?: string
  history_id?: number
  planting_window?: string | null
  harvest_window?: string | null
  evidence_ids?: string[]
}

export interface RotationOption {
  option_id: string
  strategy_type?: string
  seasons: RotationSeason[]
  score: number | null
  confidence: { status: string; reason?: string } | null
  why_suggested: string
  traits_considered: CropCharacteristic[]
  constraints_satisfied: Array<Record<string, unknown>>
  constraints_not_evaluated: Array<Record<string, unknown>>
  history_considered?: Array<Record<string, unknown>>
  environmental_inputs_considered?: Array<Record<string, unknown>>
  farmer_priorities_considered?: Record<string, number>
  evidence: string[]
  data_gaps: string[]
  assumptions: string[]
}

export interface RotationAssessment {
  recommendation_id: string
  farm_id: number
  generated_at: string
  engine_version: string
  status: 'OPTIONS_AVAILABLE' | 'INSUFFICIENT_EVIDENCE' | string
  planning_horizon: { season_count: number; start_date?: string; calendar_version: string | null }
  data_completeness: { status: string; value: number | null; reason: string }
  input_sha256: string
  options: RotationOption[]
  missing: Array<{ name: string; reason: string }>
  constraints: Array<Record<string, unknown>>
  methodology?: { id: string; version: string }
  rejected_alternatives: Array<{ candidate?: string; constraint?: string; reason: string }>
  environmental_inputs: Array<Record<string, unknown>>
  crop_profiles: Array<{
    crop_code: string
    name: string
    crop_family: string | null
    characteristics: CropCharacteristic[]
    conflicting_traits?: string[]
  }>
  farm_geometry?: unknown
  farm_location?: unknown
  farmer_context: Record<string, unknown>
  data_limitations: string[]
  explanation: { why_presented: string; methodology: string }
}

export interface RotationRequest {
  region_code?: string
  planning_seasons?: number
  planning_start_date?: string
  priority_weights?: Record<string, number>
}

export interface RotationComparison {
  recommendation_ids: string[]
  same_input: boolean
  assessments: RotationAssessment[]
  comparison_method: string
}

export interface RotationExplanation {
  recommendation_id: string
  explanation: RotationAssessment['explanation']
  missing: RotationAssessment['missing']
  constraints: RotationAssessment['constraints']
  rejected_alternatives: RotationAssessment['rejected_alternatives']
  environmental_inputs: RotationAssessment['environmental_inputs']
  crop_profiles: RotationAssessment['crop_profiles']
  data_limitations: string[]
  input_sha256: string
}

export { type Farm, type FarmerContext }

export function listCropProfiles(regionCode: string): Promise<Paginated<CropSummary>> {
  return apiRequest<Paginated<CropSummary>>(`/api/v1/crops/?region_code=${encodeURIComponent(regionCode)}`, { auth: true })
}

export function getCropProfile(cropId: number): Promise<CropProfile> {
  return apiRequest<CropProfile>(`/api/v1/crops/${cropId}/profiles/`, { auth: true })
}

export function getCropCalendar(regionCode: string): Promise<CropCalendar> {
  return apiRequest<CropCalendar>(`/api/v1/regions/${encodeURIComponent(regionCode)}/crop-calendar/`, { auth: true })
}

export function getRotationEnvironment(farmId: number): Promise<EnvironmentCurrent> {
  return apiRequest<EnvironmentCurrent>(`/api/v1/farms/${farmId}/environment/current/`, { auth: true })
}

export function generateRotation(farmId: number, payload: RotationRequest): Promise<RotationAssessment> {
  return apiRequest<RotationAssessment>(`/api/v1/farms/${farmId}/recommendations/`, {
    method: 'POST', body: payload, auth: true,
  })
}

export function getRotationAssessment(recommendationId: string): Promise<RotationAssessment> {
  return apiRequest<RotationAssessment>(`/api/v1/recommendations/${recommendationId}/`, { auth: true })
}

export function getRotationExplanation(recommendationId: string): Promise<RotationExplanation> {
  return apiRequest<RotationExplanation>(`/api/v1/recommendations/${recommendationId}/explanation/`, { auth: true })
}

export function compareRotations(firstId: string, secondId: string): Promise<RotationComparison> {
  return apiRequest<RotationComparison>(`/api/v1/recommendations/${firstId}/compare/?with=${encodeURIComponent(secondId)}`, { auth: true })
}

export function getFarmsForRotation(): Promise<Paginated<Farm>> {
  return apiRequest<Paginated<Farm>>('/api/v1/farms/', { auth: true })
}

export function getRotationFarmContext(farmId: number): Promise<FarmerContext> {
  return apiRequest<FarmerContext>(`/api/v1/farms/${farmId}/context/`, { auth: true })
}
