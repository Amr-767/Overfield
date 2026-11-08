import { describe, expect, it } from 'vitest'

import {
  buildContextPayload,
  buildFarmCreatePayload,
  createEmptyDraft,
  draftAreaSummary,
  mergeDraft,
  normalizePriorities,
  validateBoundary,
  validateFarmDetails,
  validateProfile,
  type OnboardingDraft,
} from './onboarding'

const POLYGON: OnboardingDraft['boundary'] = {
  type: 'Polygon',
  coordinates: [
    [
      [30.9501, 30.7901],
      [30.9522, 30.7901],
      [30.9522, 30.7918],
      [30.9501, 30.7918],
      [30.9501, 30.7901],
    ],
  ],
}

function readyDraft(patch: Partial<OnboardingDraft> = {}): OnboardingDraft {
  const draft = createEmptyDraft()
  draft.farm = {
    name: 'North Field',
    countryCode: 'EG',
    regionCode: 'Gharbia',
    timezone: 'Africa/Cairo',
  }
  draft.boundary = POLYGON
  draft.boundaryAreaHa = '3.7882'
  return { ...draft, ...patch }
}

describe('validateProfile', () => {
  it('accepts empty email and display name', () => {
    expect(validateProfile(createEmptyDraft())).toEqual({})
  })

  it('rejects an invalid email', () => {
    const draft = createEmptyDraft()
    draft.profile.email = 'not-an-email'
    expect(validateProfile(draft).email).toBeTruthy()
  })
})

describe('validateFarmDetails', () => {
  it('requires a farm name', () => {
    expect(validateFarmDetails(createEmptyDraft()).name).toMatch(/name/i)
  })

  it('rejects a country code that is not two letters', () => {
    const draft = createEmptyDraft()
    draft.farm.name = 'Field'
    draft.farm.countryCode = 'EGY'
    expect(validateFarmDetails(draft).countryCode).toBeTruthy()
  })

  it('accepts a completed step', () => {
    expect(validateFarmDetails(readyDraft())).toEqual({})
  })
})

describe('validateBoundary', () => {
  it('requires a polygon in boundary mode', () => {
    const draft = readyDraft({ boundary: null })
    expect(validateBoundary(draft).boundary).toBeTruthy()
  })

  it('requires a marker and reported area in point mode', () => {
    const draft = readyDraft({ mode: 'point', boundary: null, marker: null })
    const errors = validateBoundary(draft)
    expect(errors.marker).toBeTruthy()
    expect(errors.reportedAreaHa).toBeTruthy()
  })

  it('accepts a point plus a reported area', () => {
    const draft = readyDraft({
      mode: 'point',
      boundary: null,
      marker: { type: 'Point', coordinates: [30.95, 30.79] },
      reportedAreaHa: '2.5',
    })
    expect(validateBoundary(draft)).toEqual({})
  })

  it('rejects a reported area above the backend cap', () => {
    const draft = readyDraft({
      mode: 'point',
      boundary: null,
      marker: { type: 'Point', coordinates: [30.95, 30.79] },
      reportedAreaHa: '12000',
    })
    expect(validateBoundary(draft).reportedAreaHa).toBeTruthy()
  })
})

describe('normalizePriorities', () => {
  it('returns an empty object when every slider is zero', () => {
    expect(
      normalizePriorities({
        waterConservation: 0,
        soilRegeneration: 0,
        marketIncome: 0,
        forageValue: 0,
      }),
    ).toEqual({})
  })

  it('normalises weights to sum to one', () => {
    const weights = normalizePriorities({
      waterConservation: 6,
      soilRegeneration: 2,
      marketIncome: 1,
      forageValue: 1,
    })
    const total = Object.values(weights).reduce((sum, value) => sum + value, 0)
    expect(Object.keys(weights).sort()).toEqual([
      'forage_value',
      'market_income',
      'soil_regeneration',
      'water_conservation',
    ])
    expect(Math.abs(total - 1)).toBeLessThan(0.0001)
    expect(weights.water_conservation).toBeCloseTo(0.6, 3)
  })

  it('normalises a single non-zero priority to 100%', () => {
    const weights = normalizePriorities({
      waterConservation: 0,
      soilRegeneration: 0,
      marketIncome: 0,
      forageValue: 7,
    })
    expect(weights.forage_value).toBe(1)
  })
})

describe('buildFarmCreatePayload', () => {
  it('submits the drawn GeoJSON boundary unchanged (lon, lat order)', () => {
    const payload = buildFarmCreatePayload(readyDraft())
    expect(payload.boundary).toEqual(POLYGON)
    expect(payload.name).toBe('North Field')
    expect(payload.country_code).toBe('EG')
    expect(payload.timezone).toBe('Africa/Cairo')
    expect(payload.farmer_reported_area_hectares).toBeUndefined()
    // Coordinates are [longitude, latitude], never swapped.
    const first = (payload.boundary as { coordinates: number[][][] }).coordinates[0][0]
    expect(first).toEqual([30.9501, 30.7901])
  })

  it('submits a location point plus the farmer-reported area in point mode', () => {
    const draft = readyDraft({
      mode: 'point',
      boundary: null,
      boundaryAreaHa: null,
      marker: { type: 'Point', coordinates: [30.95, 30.79] },
      reportedAreaHa: '2.5',
    })
    const payload = buildFarmCreatePayload(draft)
    expect(payload.boundary).toBeUndefined()
    expect(payload.location).toEqual({ type: 'Point', coordinates: [30.95, 30.79] })
    expect(payload.farmer_reported_area_hectares).toBe('2.5')
  })

  it('throws when a boundary is missing in boundary mode', () => {
    expect(() => buildFarmCreatePayload(readyDraft({ boundary: null }))).toThrow(/boundary/i)
  })
})

describe('buildContextPayload', () => {
  it('sends null for unknown measurements and keeps only filled crops', () => {
    const draft = readyDraft()
    draft.soil.ph = ''
    draft.crops = [
      { season: 'Winter 2025/26', crop: 'Wheat' },
      { season: '', crop: 'Ignored' },
    ]
    const payload = buildContextPayload(draft)
    expect(payload.ph).toBeNull()
    expect(payload.texture_class).toBe('')
    expect(payload.irrigation_available).toBeNull()
    expect(payload.current_crops).toEqual([
      { season: 'Winter 2025/26', crop: 'Wheat', source: 'FARMER_REPORTED' },
    ])
  })

  it('maps soil and water answers to backend fields', () => {
    const draft = readyDraft()
    draft.soil = {
      ...draft.soil,
      source: 'LAB_TEST',
      textureClass: 'clay_loam',
      ph: '7.8',
      nitrogen: '22.5',
      samplingDepth: '30',
      sampleDate: '2026-03-15',
    }
    draft.water = {
      irrigationAvailable: 'yes',
      irrigationType: 'surface_canal',
      reliability: 'seasonal_variable',
    }
    draft.constraints.noMachinery = true
    draft.constraints.familyLaborOnly = true

    const payload = buildContextPayload(draft)
    expect(payload.soil_source).toBe('LAB_TEST')
    expect(payload.texture_class).toBe('clay_loam')
    expect(payload.ph).toBe('7.8')
    expect(payload.nitrogen_ppm).toBe('22.5')
    expect(payload.sampling_depth_cm).toBe(30)
    expect(payload.sample_date).toBe('2026-03-15')
    expect(payload.irrigation_available).toBe(true)
    expect(payload.irrigation_type).toBe('surface_canal')
    expect(payload.constraints).toEqual({
      equipment: ['no_mechanized_harvester'],
      labor_availability: 'family_labor_only',
    })
  })

  it('omits constraints that were left at their defaults', () => {
    const payload = buildContextPayload(readyDraft())
    expect(payload.constraints).toEqual({})
  })
})

describe('draftAreaSummary', () => {
  it('labels a computed boundary area as high precision', () => {
    const summary = draftAreaSummary(readyDraft())
    expect(summary.hectares).toBe('3.7882')
    expect(summary.precision).toBe('HIGH')
    expect(summary.label).toMatch(/calculated/i)
  })

  it('labels a farmer-reported area as low precision', () => {
    const summary = draftAreaSummary(
      readyDraft({ mode: 'point', boundary: null, reportedAreaHa: '2.5' }),
    )
    expect(summary.precision).toBe('LOW')
    expect(summary.label).toMatch(/not GIS/i)
  })

  it('reports nothing when no area is available', () => {
    expect(draftAreaSummary(createEmptyDraft()).hectares).toBeNull()
  })
})

describe('mergeDraft', () => {
  it('keeps defaults for missing nested keys', () => {
    const merged = mergeDraft(createEmptyDraft(), {
      farm: { name: 'Stored farm' },
      crops: [{ season: 'Summer 2026', crop: 'Rice' }],
    })
    expect(merged.farm.name).toBe('Stored farm')
    expect(merged.farm.timezone).toBe('Africa/Cairo')
    expect(merged.crops).toHaveLength(1)
    expect(merged.soil.textureClass).toBe('')
  })

  it('ignores non-object input', () => {
    const base = createEmptyDraft()
    expect(mergeDraft(base, null)).toEqual(base)
    expect(mergeDraft(base, 'nonsense')).toEqual(base)
  })
})
