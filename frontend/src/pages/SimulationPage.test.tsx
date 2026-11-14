// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/types'

const mocks = vi.hoisted(() => ({ farms: vi.fn(), create: vi.fn(), history: vi.fn() }))

vi.mock('../api/farms', () => ({ listFarms: mocks.farms }))

vi.mock('../api/simulations', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/simulations')>()
  return { ...actual, createSimulation: mocks.create, listSimulations: mocks.history }
})

import { SimulationPage } from './SimulationPage'

const farm = {
  id: 12,
  name: 'Test farm',
  country_code: 'EG',
  region_code: 'EG-GH',
  boundary: null,
  location: null,
  area_hectares: '2.5000',
  area_source: 'FARMER_REPORTED',
  geometry_source: 'LOCATION_POINT',
  spatial_precision: 'LOW',
  timezone: 'Africa/Cairo',
  zone_count: 0,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const metrics = {
  mean_temperature_c: '16.04',
  mean_max_temperature_c: '22.84',
  mean_min_temperature_c: '10.66',
  rainfall_total_mm: '0.51',
  rainy_days: 0,
  hot_days_max_temperature_ge_35c: 0,
  very_hot_days_max_temperature_ge_40c: 0,
  cool_nights_min_temperature_le_5c: 0,
  days_with_mean_temperature: 7,
  days_with_rainfall: 7,
}

const scenario = {
  mode: 'HOT_SCENARIO',
  label: 'Hot scenario — +2.00 °C on stored temperatures',
  temperature_delta_c: '2.00',
  rainfall_multiplier: '1.00',
  is_hypothetical: true,
  adjustment_basis: 'USER_DECLARED_ASSUMPTION',
  bounds: {
    temperature_delta_c: ['-5.00', '5.00'] as [string, string],
    rainfall_multiplier: ['0.20', '2.00'] as [string, string],
  },
}

function step(overrides: Record<string, unknown> = {}) {
  return {
    checkpoint: 'PRESENT',
    label: 'Present — stored observation window',
    horizon_months: 0,
    as_of_date: null,
    status: 'COMPLETED',
    metrics: { ...metrics, mean_temperature_c: '18.04' },
    missing_inputs: [],
    applied_adjustments: {
      temperature_delta_c: '2.00',
      rainfall_multiplier: '1.00',
      applied_to: ['T2M', 'T2M_MAX', 'T2M_MIN', 'PRECTOTCORR'],
    },
    assumptions: ['The declared adjustment is applied to stored observations from 2024-01-01 to 2024-01-07.'],
    limitations: ['Scenario adjustments are user-declared hypothetical assumptions.'],
    ...overrides,
  }
}

function run(overrides: Record<string, unknown> = {}) {
  return {
    simulation_id: '11111111-1111-4111-8111-111111111111',
    farm_id: 12,
    scenario,
    engine_version: 'phase6-env-1.0.0',
    status: 'COMPLETED',
    baseline: {
      period: {
        start: '2024-01-01',
        end: '2024-01-07',
        latest_observation: '2024-01-07',
        days_expected: 7,
        freshness: 'STALE',
      },
      metrics,
      parameters: {
        T2M: { units: 'C', available_days: 7, missing_days: 0 },
        PRECTOTCORR: { units: 'mm/day', available_days: 7, missing_days: 0 },
      },
      sources: [
        {
          provider: 'NASA_POWER',
          parameter: 'T2M',
          units: 'C',
          product: 'MERRA-2',
          data_category: 'REANALYSIS_OR_ASSIMILATION_ESTIMATE',
          native_resolution_note: null,
          time_standard: 'UTC',
          access_date: null,
        },
      ],
      missing_inputs: [],
    },
    differences: {
      mean_temperature_c: { baseline: '16.04', scenario: '18.04', change: '2.00' },
      hot_days_max_temperature_ge_35c: { baseline: 0, scenario: 7, change: 7 },
    },
    comparison: {
      supported: true,
      method: 'Recorded evidence differences only. No score, rank, winner or recommendation is produced.',
      ranked: false,
      score: null,
    },
    crop_level_outcomes: 'NOT_SIMULATED',
    hypothetical_notice:
      'Scenario adjustments are user-declared hypothetical assumptions applied to stored NASA POWER observations. They are not a NASA forecast, prediction or measurement.',
    limitations: [
      'Scenario adjustments are user-declared hypothetical assumptions applied to stored NASA POWER observations. They are not a NASA forecast, prediction or measurement.',
      'No approved regional crop calendar exists, so crop-level scenario outcomes are not simulated.',
    ],
    steps: [
      step(),
      step({ checkpoint: 'PLUS_6_MONTHS', label: '+6 months — repeated-observation horizon', horizon_months: 6 }),
      step({ checkpoint: 'PLUS_1_YEAR', label: '+1 year — repeated-observation horizon', horizon_months: 12 }),
      step({ checkpoint: 'PLUS_2_YEARS', label: '+2 years — repeated-observation horizon', horizon_months: 24 }),
    ],
    input_sha256: 'a'.repeat(64),
    created_at: '2026-11-14T10:00:00Z',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function chooseFarmAndRun() {
  const user = userEvent.setup()
  await user.selectOptions(await screen.findByLabelText('Farm'), '12')
  await user.click(screen.getByRole('button', { name: 'Run hypothetical scenario' }))
  return user
}

beforeEach(() => {
  mocks.farms.mockResolvedValue({ count: 1, next: null, previous: null, results: [farm] })
  mocks.history.mockResolvedValue({ count: 0, results: [] })
  mocks.create.mockResolvedValue(run())
})
afterEach(cleanup)

describe('SimulationPage', () => {
  it('shows an honest empty state when the account has no farms', async () => {
    mocks.farms.mockResolvedValueOnce({ count: 0, next: null, previous: null, results: [] })
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Start with a farm' })).toBeTruthy()
  })

  it('renders the hypothetical result, the recorded difference and the fingerprint', async () => {
    renderPage()
    await chooseFarmAndRun()

    expect(
      await screen.findByText('Hot scenario — +2.00 °C on stored temperatures'),
    ).toBeTruthy()
    expect(
      screen.getAllByText(/are not a NASA forecast, prediction or measurement/).length,
    ).toBeGreaterThan(0)
    expect(screen.getByText(/Recorded difference/)).toBeTruthy()
    expect(screen.getAllByText('18.04 °C').length).toBeGreaterThan(0)
    expect(screen.getByText('a'.repeat(64))).toBeTruthy()
    expect(screen.getByText('No future dates asserted')).toBeTruthy()
  })

  it('reports insufficient evidence instead of inventing a scenario value', async () => {
    mocks.create.mockResolvedValueOnce(
      run({
        status: 'INSUFFICIENT_EVIDENCE',
        baseline: {
          ...run().baseline,
          metrics: null,
          missing_inputs: ['NASA POWER environmental observations for this farm'],
        },
        differences: {},
        steps: [
          step({
            status: 'INSUFFICIENT_EVIDENCE',
            metrics: {},
            missing_inputs: ['NASA POWER environmental observations for this farm'],
          }),
        ],
      }),
    )
    renderPage()
    await chooseFarmAndRun()

    expect(await screen.findByText('No usable stored observations for this farm')).toBeTruthy()
    expect(screen.getByText('No environmental metrics available')).toBeTruthy()
  })

  it('shows a validation error when a crop-level request is refused', async () => {
    mocks.create.mockRejectedValueOnce(
      new ApiError('Invalid', 400, {
        planning_seasons: [
          'Crop-level simulation requires an approved regional crop catalogue and calendar.',
        ],
      }),
    )
    renderPage()
    await chooseFarmAndRun()

    expect((await screen.findByRole('alert')).textContent).toMatch(
      /approved regional crop catalogue/,
    )
  })

  it('reveals the bounded custom controls only in custom mode', async () => {
    renderPage()
    const user = userEvent.setup()
    await screen.findByLabelText('Farm')

    expect(screen.queryByLabelText('Temperature delta (°C)')).toBeNull()
    await user.selectOptions(screen.getByLabelText('Scenario'), 'CUSTOM')

    expect(screen.getByLabelText('Temperature delta (°C)')).toBeTruthy()
    expect(screen.getByLabelText('Rainfall multiplier')).toBeTruthy()
  })
})
