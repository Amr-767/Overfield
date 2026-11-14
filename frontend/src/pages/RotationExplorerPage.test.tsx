// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/types'

const mocks = vi.hoisted(() => ({
  farms: vi.fn(), context: vi.fn(), environment: vi.fn(), catalog: vi.fn(), calendar: vi.fn(), generate: vi.fn(),
}))

vi.mock('../api/rotation', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/rotation')>()
  return {
    ...actual,
    getFarmsForRotation: mocks.farms,
    getRotationFarmContext: mocks.context,
    getRotationEnvironment: mocks.environment,
    listCropProfiles: mocks.catalog,
    getCropCalendar: mocks.calendar,
    generateRotation: mocks.generate,
    getCropProfile: vi.fn().mockResolvedValue({
      id: 3, code: 'TEST_CROP', name: 'Fixture crop', scientific_name: '', crop_family: '', source_status: 'VALID', evidence_ids: ['fixture-evidence'],
      characteristics: [], missing_characteristics: ['water_requirement'],
    }),
    getRotationAssessment: vi.fn(),
    getRotationExplanation: vi.fn().mockResolvedValue({
      recommendation_id: '11111111-1111-4111-8111-111111111111',
      explanation: { why_presented: 'Historical comparison only.', methodology: 'No ranking.' },
      missing: [], constraints: [], rejected_alternatives: [], environmental_inputs: [],
      crop_profiles: [], data_limitations: [], input_sha256: 'abc123',
    }),
    compareRotations: vi.fn(),
  }
})

vi.mock('../components/FarmMap', () => ({ FarmMap: () => <div data-testid="farm-map">Map preview</div> }))

import { RotationExplorerPage } from './RotationExplorerPage'

const farm = {
  id: 12, name: 'Test farm', country_code: 'EG', region_code: 'EG-GH', boundary: null,
  location: null, area_hectares: '2.5000', area_source: 'FARMER_REPORTED', geometry_source: 'LOCATION_POINT',
  spatial_precision: 'LOW', timezone: 'Africa/Cairo', zone_count: 0, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
}

function assessment(overrides: Record<string, unknown> = {}) {
  return {
    recommendation_id: '11111111-1111-4111-8111-111111111111', farm_id: 12,
    generated_at: '2026-01-01T00:00:00Z', engine_version: 'rotation-v1.0', status: 'INSUFFICIENT_EVIDENCE',
    planning_horizon: { season_count: 4, start_date: '2026-01-01', calendar_version: null },
    data_completeness: { status: 'NOT_ASSESSED', value: null, reason: 'No method.' }, input_sha256: 'abc123', options: [],
    missing: [{ name: 'crop_profiles', reason: 'No approved crop profiles.' }], constraints: [], rejected_alternatives: [],
    environmental_inputs: [], crop_profiles: [], farmer_context: {}, data_limitations: ['No real-time conditions.'],
    explanation: { why_presented: 'Evidence readiness only.', methodology: 'No scoring.' }, ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><MemoryRouter><RotationExplorerPage /></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  mocks.farms.mockResolvedValue({ count: 1, next: null, previous: null, results: [farm] })
  mocks.context.mockResolvedValue({ farm_id: 12, current_crops: [], priorities: {}, texture_class: '', sample_date: null, irrigation_available: null })
  mocks.environment.mockResolvedValue({ farm_id: 12, generated_at: '2026-01-01', window: { start: '2025-12-01', end: '2025-12-01', days: 30, latest_observation: null, age_days: null, freshness: 'UNKNOWN' }, data_status: 'INSUFFICIENT_DATA', indicators: {}, limitations: [] })
  mocks.catalog.mockResolvedValue({ count: 0, next: null, previous: null, results: [] })
  mocks.calendar.mockRejectedValue(new ApiError('Not found', 404))
  mocks.generate.mockResolvedValue(assessment())
})
afterEach(cleanup)

describe('RotationExplorerPage', () => {
  it('shows a real empty state when the account has no farms', async () => {
    mocks.farms.mockResolvedValueOnce({ count: 0, next: null, previous: null, results: [] })
    renderPage()
    expect(await screen.findByRole('heading', { name: 'Start with a farm' })).toBeTruthy()
  })

  it('presents the backend insufficient-evidence result and keeps missing data visible', async () => {
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Explore rotation options' }))
    expect(await screen.findByText('There is not enough evidence to recommend a rotation')).toBeTruthy()
    expect(screen.getByText('No feasible rotation options returned')).toBeTruthy()
    expect(screen.getByText('No approved crop profiles.')).toBeTruthy()
    expect(screen.getByText('No eligible crop profiles available')).toBeTruthy()
    expect(screen.getByTestId('farm-map')).toBeTruthy()
  })

  it('shows a candidate option but never renders a null score as zero', async () => {
    mocks.generate.mockResolvedValueOnce(assessment({
      status: 'OPTIONS_AVAILABLE',
      options: [{ option_id: 'rotation-a', strategy_type: 'BASELINE', seasons: [{ season_code: 'S1', crop_code: 'A', crop_name: 'Crop A', source: 'USER_PROVIDED' }], score: null, confidence: { status: 'NOT_ASSESSED' }, why_suggested: 'Historical comparison only.', traits_considered: [], constraints_satisfied: [], constraints_not_evaluated: [], evidence: [], data_gaps: [], assumptions: [] }],
    }))
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Explore rotation options' }))
    expect(await screen.findByRole('heading', { name: 'Your recorded history' })).toBeTruthy()
    expect(screen.getByText('Score: not assessed')).toBeTruthy()
    expect(screen.queryByText(/^0$/)).toBeNull()
    await userEvent.click(screen.getByRole('button', { name: 'Read explanation' }))
    expect(screen.getAllByText('Historical comparison only.').length).toBeGreaterThan(1)
  })

  it('renders expired-session and API errors accessibly', async () => {
    mocks.generate.mockRejectedValueOnce(new ApiError('Your session has expired.', 401))
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Explore rotation options' }))
    expect(await screen.findByText('Your session has expired. Sign in again to continue.')).toBeTruthy()
  })

  it('shows stale environmental context as stale instead of current', async () => {
    mocks.environment.mockResolvedValueOnce({
      farm_id: 12, generated_at: '2026-01-01',
      window: { start: '2024-12-01', end: '2024-12-01', days: 30, latest_observation: '2024-12-01', age_days: 396, freshness: 'STALE' },
      data_status: 'PARTIAL', indicators: {}, limitations: [],
    })
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    expect(await screen.findByText('Latest observation Dec 1, 2024')).toBeTruthy()
    expect(screen.getByText('Stale')).toBeTruthy()
  })

  it('opens a crop profile and marks missing characteristics as not recorded', async () => {
    mocks.catalog.mockResolvedValueOnce({ count: 1, next: null, previous: null, results: [{
      id: 3, code: 'TEST_CROP', name: 'Fixture crop', scientific_name: '', crop_family: '',
      source_status: 'VALID', evidence_ids: ['fixture-evidence'],
    }] })
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    await userEvent.click(await screen.findByRole('button', { name: 'View evidence' }))
    expect(await screen.findByRole('dialog')).toBeTruthy()
    expect(screen.getByText(/water requirement/)).toBeTruthy()
    expect(screen.getByText('Not recorded')).toBeTruthy()
  })

  it('compares two options side-by-side without declaring a winner', async () => {
    mocks.generate.mockResolvedValueOnce(assessment({ status: 'OPTIONS_AVAILABLE', options: [
      { option_id: 'option-a', strategy_type: 'BASELINE', seasons: [{ season_code: 'S1', crop_code: 'A', crop_name: 'Crop A' }], score: null, confidence: null, why_suggested: 'Evidence A.', traits_considered: [], constraints_satisfied: [], constraints_not_evaluated: [], evidence: ['ev-a'], data_gaps: [], assumptions: [] },
      { option_id: 'option-b', seasons: [{ season_code: 'S1', crop_code: 'B', crop_name: 'Crop B' }], score: null, confidence: null, why_suggested: 'Evidence B.', traits_considered: [], constraints_satisfied: [], constraints_not_evaluated: [], evidence: ['ev-b'], data_gaps: [], assumptions: [] },
    ] }))
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Explore rotation options' }))
    await screen.findByText('Evidence A.')
    const selectButtons = screen.getAllByRole('button', { name: 'Select to compare' })
    await userEvent.click(selectButtons[0])
    await userEvent.click(selectButtons[1])
    expect(await screen.findByRole('heading', { name: 'Side-by-side evidence comparison' })).toBeTruthy()
    expect(screen.getByText(/does not rank them or declare a winner/i)).toBeTruthy()
  })

  it('renders candidate comparison structure and does not claim a winner', async () => {
    mocks.generate.mockResolvedValueOnce(assessment({ status: 'OPTIONS_AVAILABLE', options: [] }))
    renderPage()
    await userEvent.selectOptions(await screen.findByLabelText('Farm'), '12')
    await userEvent.click(screen.getByRole('button', { name: 'Explore rotation options' }))
    expect(await screen.findByText('No feasible rotation options returned')).toBeTruthy()
    expect(screen.getByText(/comparisons report evidence differences, not a best option/i)).toBeTruthy()
  })
})
