/** Pure onboarding draft logic: validation and API payload construction. */

import type {
  BoundaryGeometry,
  FarmerConstraints,
  FarmerContextPayload,
  FarmCreatePayload,
  PointGeometry,
  Provenance,
} from '../api/types'

export type BoundaryMode = 'boundary' | 'point'

export interface ProfileDraft {
  displayName: string
  email: string
  preferredLanguage: string
}

export interface FarmDetailsDraft {
  name: string
  countryCode: string
  regionCode: string
  timezone: string
}

export interface SoilDraft {
  source: Provenance
  textureClass: string
  ph: string
  organicCarbon: string
  nitrogen: string
  phosphorus: string
  potassium: string
  samplingDepth: string
  labName: string
  sampleDate: string
}

export interface WaterDraft {
  irrigationAvailable: '' | 'yes' | 'no'
  irrigationType: string
  reliability: string
}

export interface CropDraft {
  season: string
  crop: string
}

export interface PriorityDraft {
  waterConservation: number
  soilRegeneration: number
  marketIncome: number
  forageValue: number
}

export interface ConstraintsDraft {
  noMachinery: boolean
  familyLaborOnly: boolean
  seedAvailability: string
}

export interface OnboardingDraft {
  profile: ProfileDraft
  farm: FarmDetailsDraft
  mode: BoundaryMode
  boundary: BoundaryGeometry | null
  boundaryAreaHa: string | null
  marker: PointGeometry | null
  reportedAreaHa: string
  soil: SoilDraft
  water: WaterDraft
  crops: CropDraft[]
  priorities: PriorityDraft
  constraints: ConstraintsDraft
}

export type DraftErrors = Record<string, string>

export const PRIORITY_FIELDS: ReadonlyArray<{
  key: keyof PriorityDraft
  apiKey: string
  label: string
  hint: string
}> = [
  {
    key: 'waterConservation',
    apiKey: 'water_conservation',
    label: 'Save water',
    hint: 'Keep irrigation use low and protect against dry spells.',
  },
  {
    key: 'soilRegeneration',
    apiKey: 'soil_regeneration',
    label: 'Improve the soil',
    hint: 'Build organic matter and reduce soil fatigue.',
  },
  {
    key: 'marketIncome',
    apiKey: 'market_income',
    label: 'Market income',
    hint: 'Favour crops with reliable local demand.',
  },
  {
    key: 'forageValue',
    apiKey: 'forage_value',
    label: 'Feed for livestock',
    hint: 'Produce fodder or grazing value.',
  },
]

export const TEXTURE_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: '', label: 'Not sure' },
  { value: 'sand', label: 'Sandy' },
  { value: 'loamy_sand', label: 'Sandy loam' },
  { value: 'sandy_loam', label: 'Sandy loam (heavier)' },
  { value: 'loam', label: 'Loam' },
  { value: 'silt_loam', label: 'Silt loam' },
  { value: 'silt', label: 'Silt' },
  { value: 'clay_loam', label: 'Clay loam' },
  { value: 'sandy_clay_loam', label: 'Sandy clay loam' },
  { value: 'silty_clay_loam', label: 'Silty clay loam' },
  { value: 'clay', label: 'Clay' },
  { value: 'sandy_clay', label: 'Sandy clay' },
  { value: 'silty_clay', label: 'Silty clay' },
  { value: 'unknown', label: 'Unknown' },
]

export const IRRIGATION_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: '', label: 'Not sure' },
  { value: 'none', label: 'Rain-fed only' },
  { value: 'surface_canal', label: 'Canal / surface' },
  { value: 'drip', label: 'Drip' },
  { value: 'sprinkler', label: 'Sprinkler' },
  { value: 'flood', label: 'Flood' },
  { value: 'mixed', label: 'Mixed' },
  { value: 'other', label: 'Other' },
  { value: 'unknown', label: 'Unknown' },
]

export const RELIABILITY_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: '', label: 'Not sure' },
  { value: 'reliable', label: 'Reliable' },
  { value: 'seasonal_variable', label: 'Varies by season' },
  { value: 'unreliable', label: 'Often short' },
  { value: 'unknown', label: 'Unknown' },
]

export const SEED_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'unknown', label: 'Not sure' },
  { value: 'available_locally', label: 'Available locally' },
  { value: 'difficult_to_source', label: 'Hard to find' },
]

export const SOIL_SOURCES: ReadonlyArray<{ value: Provenance; label: string }> = [
  { value: 'FARMER_REPORTED', label: 'From my own knowledge' },
  { value: 'LAB_TEST', label: 'From a soil test / laboratory' },
]

export function createEmptyDraft(): OnboardingDraft {
  return {
    profile: { displayName: '', email: '', preferredLanguage: 'en' },
    farm: { name: '', countryCode: 'EG', regionCode: '', timezone: 'Africa/Cairo' },
    mode: 'boundary',
    boundary: null,
    boundaryAreaHa: null,
    marker: null,
    reportedAreaHa: '',
    soil: {
      source: 'FARMER_REPORTED',
      textureClass: '',
      ph: '',
      organicCarbon: '',
      nitrogen: '',
      phosphorus: '',
      potassium: '',
      samplingDepth: '',
      labName: '',
      sampleDate: '',
    },
    water: { irrigationAvailable: '', irrigationType: '', reliability: '' },
    crops: [{ season: '', crop: '' }],
    priorities: {
      waterConservation: 5,
      soilRegeneration: 5,
      marketIncome: 5,
      forageValue: 5,
    },
    constraints: { noMachinery: false, familyLaborOnly: false, seedAvailability: 'unknown' },
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

/** Merge a stored draft over the defaults so older/incomplete drafts still load. */
export function mergeDraft(base: OnboardingDraft, stored: unknown): OnboardingDraft {
  if (!isRecord(stored)) return base
  const merged: Record<string, unknown> = { ...base }
  const baseRecord = base as unknown as Record<string, unknown>

  for (const key of Object.keys(baseRecord)) {
    const baseValue = baseRecord[key]
    const storedValue = stored[key]
    if (isRecord(baseValue) && isRecord(storedValue)) {
      merged[key] = { ...baseValue, ...storedValue }
    } else if (Array.isArray(baseValue) && Array.isArray(storedValue)) {
      merged[key] = storedValue
    } else if (storedValue !== undefined) {
      merged[key] = storedValue
    }
  }
  return merged as unknown as OnboardingDraft
}

function validCountryCode(value: string): boolean {
  return value === '' || /^[A-Za-z]{2}$/.test(value.trim())
}

function validEmail(value: string): boolean {
  return value === '' || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

export function validateProfile(draft: OnboardingDraft): DraftErrors {
  const errors: DraftErrors = {}
  if (!validEmail(draft.profile.email)) {
    errors.email = 'Enter a valid email address, or leave it empty.'
  }
  if (draft.profile.displayName.length > 120) {
    errors.displayName = 'Display name must be 120 characters or fewer.'
  }
  return errors
}

export function validateFarmDetails(draft: OnboardingDraft): DraftErrors {
  const errors: DraftErrors = {}
  if (!draft.farm.name.trim()) {
    errors.name = 'Give your farm a name so you can find it later.'
  } else if (draft.farm.name.trim().length > 120) {
    errors.name = 'Farm name must be 120 characters or fewer.'
  }
  if (!validCountryCode(draft.farm.countryCode)) {
    errors.countryCode = 'Use a 2-letter country code, for example EG.'
  }
  if (draft.farm.regionCode.length > 80) {
    errors.regionCode = 'Region must be 80 characters or fewer.'
  }
  if (!draft.farm.timezone.trim()) {
    errors.timezone = 'Choose the timezone used on your farm.'
  }
  return errors
}

export function validateBoundary(draft: OnboardingDraft): DraftErrors {
  const errors: DraftErrors = {}
  if (draft.mode === 'boundary') {
    if (!draft.boundary) {
      errors.boundary = 'Draw your farm boundary on the map to continue.'
    }
  } else {
    if (!draft.marker) {
      errors.marker = 'Place a point on the map for your farm location.'
    }
    const area = Number(draft.reportedAreaHa)
    if (!draft.reportedAreaHa.trim() || Number.isNaN(area) || area <= 0) {
      errors.reportedAreaHa = 'Enter your approximate farm size in hectares.'
    } else if (area > 10000) {
      errors.reportedAreaHa = 'That is larger than 10,000 ha. Please check the value.'
    }
  }
  return errors
}

export function validateAll(draft: OnboardingDraft): DraftErrors {
  return {
    ...validateProfile(draft),
    ...validateFarmDetails(draft),
    ...validateBoundary(draft),
  }
}

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

/**
 * Convert slider positions into backend priority weights that sum to 1.
 * All-zero sliders return `{}` so the farmer can skip priorities entirely.
 */
export function normalizePriorities(priorities: PriorityDraft): Record<string, number> {
  const entries = PRIORITY_FIELDS.map((field) => [field.apiKey, Math.max(0, priorities[field.key])] as const)
  const total = entries.reduce((sum, [, value]) => sum + value, 0)
  if (total <= 0) return {}

  const weights: Record<string, number> = {}
  let assigned = 0
  entries.forEach(([key, value], index) => {
    if (index === entries.length - 1) {
      weights[key] = Number((1 - assigned).toFixed(4))
    } else {
      const weight = Number((value / total).toFixed(4))
      weights[key] = weight
      assigned += weight
    }
  })
  return weights
}

export function buildConstraints(draft: OnboardingDraft): FarmerConstraints {
  const constraints: FarmerConstraints = {}
  if (draft.constraints.noMachinery) {
    constraints.equipment = ['no_mechanized_harvester']
  }
  if (draft.constraints.familyLaborOnly) {
    constraints.labor_availability = 'family_labor_only'
  }
  if (draft.constraints.seedAvailability && draft.constraints.seedAvailability !== 'unknown') {
    constraints.seed_availability = draft.constraints.seedAvailability
  }
  return constraints
}

export function buildFarmCreatePayload(draft: OnboardingDraft): FarmCreatePayload {
  const base: FarmCreatePayload = {
    name: draft.farm.name.trim(),
    country_code: draft.farm.countryCode.trim().toUpperCase(),
    region_code: draft.farm.regionCode.trim(),
    timezone: draft.farm.timezone.trim() || 'UTC',
  }

  if (draft.mode === 'boundary') {
    if (!draft.boundary) {
      throw new Error('A boundary polygon is required to save this farm.')
    }
    // GeoJSON is submitted unchanged: [longitude, latitude] order (ADR-010).
    return { ...base, boundary: draft.boundary }
  }

  if (!draft.marker) {
    throw new Error('A location point is required to save this farm.')
  }
  return {
    ...base,
    location: draft.marker,
    farmer_reported_area_hectares: String(Number(draft.reportedAreaHa)),
  }
}

export function buildContextPayload(draft: OnboardingDraft): FarmerContextPayload {
  const { soil, water } = draft
  const crops = draft.crops
    .filter((entry) => entry.season.trim() && entry.crop.trim())
    .map((entry) => ({
      season: entry.season.trim(),
      crop: entry.crop.trim(),
      source: 'FARMER_REPORTED' as Provenance,
    }))

  return {
    soil_source: soil.source,
    texture_class: soil.textureClass,
    ph: soil.ph.trim() ? soil.ph.trim() : null,
    organic_carbon_percent: soil.organicCarbon.trim() ? soil.organicCarbon.trim() : null,
    nitrogen_ppm: soil.nitrogen.trim() ? soil.nitrogen.trim() : null,
    phosphorus_ppm: soil.phosphorus.trim() ? soil.phosphorus.trim() : null,
    potassium_ppm: soil.potassium.trim() ? soil.potassium.trim() : null,
    sampling_depth_cm: parseOptionalNumber(soil.samplingDepth),
    sampling_method: '',
    lab_name: soil.labName.trim(),
    sample_date: soil.sampleDate.trim() ? soil.sampleDate.trim() : null,
    water_source: 'FARMER_REPORTED',
    irrigation_available:
      water.irrigationAvailable === '' ? null : water.irrigationAvailable === 'yes',
    irrigation_type: water.irrigationType,
    water_reliability: water.reliability,
    priorities: normalizePriorities(draft.priorities),
    constraints: buildConstraints(draft),
    current_crops: crops,
  }
}

export function applyProfileDefaults(
  draft: OnboardingDraft,
  profile: { display_name?: string; email?: string; preferred_language?: string },
): OnboardingDraft {
  return {
    ...draft,
    profile: {
      displayName: draft.profile.displayName || profile.display_name || '',
      email: draft.profile.email || profile.email || '',
      preferredLanguage: draft.profile.preferredLanguage || profile.preferred_language || 'en',
    },
  }
}

export function draftAreaSummary(draft: OnboardingDraft): {
  hectares: string | null
  label: string
  precision: 'HIGH' | 'LOW'
} {
  if (draft.mode === 'boundary' && draft.boundaryAreaHa) {
    return {
      hectares: draft.boundaryAreaHa,
      label: 'Calculated from your boundary',
      precision: 'HIGH',
    }
  }
  if (draft.mode === 'point' && draft.reportedAreaHa) {
    return {
      hectares: draft.reportedAreaHa,
      label: 'Reported by you — not GIS-calculated',
      precision: 'LOW',
    }
  }
  return { hectares: null, label: 'Not available yet', precision: 'LOW' }
}
