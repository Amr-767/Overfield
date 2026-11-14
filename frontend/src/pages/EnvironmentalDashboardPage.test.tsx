// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/types'

const mocks = vi.hoisted(() => ({
  getFarm: vi.fn(),
  listFarms: vi.fn(),
  summary: vi.fn(),
  scan: vi.fn(),
  job: vi.fn(),
}))

vi.mock('../api/farms', () => ({ getFarm: mocks.getFarm, listFarms: mocks.listFarms }))

vi.mock('../api/environment', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/environment')>()
  return {
    ...actual,
    getEnvironmentSummary: mocks.summary,
    requestScan: mocks.scan,
    getDataJob: mocks.job,
  }
})

import { EnvironmentalDashboardPage } from './EnvironmentalDashboardPage'

function farm(id = 12, name = 'Test farm') {
  return {
    id,
    name,
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
}

function measurement(overrides: Record<string, unknown> = {}) {
  return {
    name: 'precipitation_total',
    value: '12.4000',
    unit: 'mm',
    source: 'NASA_POWER',
    parameter: 'PRECTOTCORR',
    product: 'MERRA-2',
    quality: 'AVAILABLE',
    method: 'sum of daily totals over covered days only',
    interpretation: null,
    ...overrides,
  }
}

function indicator(overrides: Record<string, unknown> = {}) {
  return {
    code: 'WATER',
    label: 'Water',
    status: 'OK',
    score: null,
    confidence: 'MEDIUM',
    as_of: '2026-11-01',
    period: {
      start: '2026-10-03',
      end: '2026-11-01',
      latest_observation: '2026-11-01',
      age_days: 13,
      freshness: 'RECENT',
    },
    coverage: {
      days_expected: 30,
      days_covered: 30,
      days_missing: 0,
      ratio: '1.0000',
      by_parameter: { PRECTOTCORR: 30 },
    },
    completeness: null,
    summary: 'All 30 days observed: 12.4 mm of rainfall over covered days.',
    measurements: [measurement()],
    context: [],
    drivers: [],
    missing: [],
    methodology: {
      id: 'water.rainfall.v1',
      version: '1.0.0',
      description: 'Rainfall summary over the latest available observation window.',
      threshold_source: 'Rainy-day threshold defaults to 1.0 mm/day.',
    },
    sources: [
      {
        provider: 'NASA_POWER',
        parameter: 'PRECTOTCORR',
        units: 'mm',
        product: 'MERRA-2',
        data_category: 'REANALYSIS_OR_ASSIMILATION_ESTIMATE',
        native_resolution_note: '0.5 x 0.625 degree grid',
        time_standard: 'UTC',
        access_date: null,
      },
    ],
    limitations: [
      'Values are NASA POWER MERRA-2 grid-cell estimates for the farm representative point, not on-farm measurements.',
    ],
    ...overrides,
  }
}

function summary(overrides: Record<string, unknown> = {}) {
  const water = indicator()
  const heat = indicator({
    code: 'HEAT',
    label: 'Heat',
    summary: 'All 30 days observed: mean temperature 19.2 °C.',
    measurements: [
      measurement({
        name: 'mean_temperature',
        value: '19.2000',
        unit: 'C',
        parameter: 'T2M',
        method: 'mean of daily mean temperature over covered days',
      }),
    ],
    sources: [
      {
        provider: 'NASA_POWER',
        parameter: 'T2M',
        units: 'C',
        product: 'MERRA-2',
        data_category: 'REANALYSIS_OR_ASSIMILATION_ESTIMATE',
        native_resolution_note: '0.5 x 0.625 degree grid',
        time_standard: 'UTC',
        access_date: null,
      },
    ],
  })
  const soil = indicator({
    code: 'SOIL',
    label: 'Soil',
    coverage: null,
    completeness: { properties_expected: 6, properties_present: 2, ratio: '0.3333' },
    summary: '2 of 6 soil properties recorded; source FARMER_REPORTED; sample dated 2026-06-01 (FRESH).',
    measurements: [
      measurement({
        name: 'ph',
        value: '7.2000',
        unit: 'pH',
        source: 'FARMER_REPORTED',
        parameter: null,
        product: null,
        quality: 'FARMER_REPORTED',
        method: 'not recorded',
        interpretation: 'NEUTRAL',
      }),
    ],
    sources: [],
    limitations: ['No composite soil-health score is produced; each property is reported on its own.'],
  })
  const market = {
    code: 'MARKET',
    label: 'Market',
    status: 'UNAVAILABLE',
    score: null,
    confidence: 'NONE',
    as_of: null,
    period: null,
    coverage: null,
    completeness: null,
    summary:
      'No verified local market price source is available for EG-GH (EG), so market value cannot be assessed. No price is estimated or invented.',
    measurements: [],
    context: [],
    drivers: [],
    missing: [
      {
        name: 'local_market_price_source',
        impact: 'No local farm-gate price can be shown.',
        required_for: 'market value',
      },
    ],
    methodology: {
      id: 'market.unavailable.v1',
      version: '1.0.0',
      description: 'Market value is not assessed: no verified local farm-gate price source exists.',
      threshold_source: 'No price thresholds or scoring are defined (decision R18).',
    },
    sources: [],
    limitations: ['No local price is estimated or invented.'],
  }

  return {
    farm_id: 12,
    generated_at: '2026-11-14T10:00:00Z',
    window: {
      start: '2026-10-03',
      end: '2026-11-01',
      days: 30,
      latest_observation: '2026-11-01',
      age_days: 13,
      freshness: 'RECENT',
    },
    data_status: 'OK',
    freshness: {
      latest_observation: '2026-11-01',
      age_days: 13,
      status: 'RECENT',
    },
    indicators: { water, heat, soil, market },
    limitations: [
      'Indicators describe the latest available observations, not real-time or forecast conditions.',
      'Environmental values are NASA POWER grid-cell estimates for the farm representative point, not on-farm measurements.',
    ],
    ...overrides,
  }
}

function dataJob(overrides: Record<string, unknown> = {}) {
  return {
    job_id: 'job-1',
    farm_id: 12,
    provider: 'NASA_POWER',
    status: 'RUNNING',
    requested_start: '2025-11-15',
    requested_end: '2026-11-11',
    parameters: ['T2M', 'PRECTOTCORR'],
    days_requested: 365,
    days_stored: null,
    days_missing: null,
    error_code: null,
    error_message: null,
    created_at: '2026-11-14T10:00:00Z',
    started_at: '2026-11-14T10:00:05Z',
    finished_at: null,
    duration_ms: null,
    status_url: '/api/v1/data-jobs/job-1/',
    ...overrides,
  }
}

function renderPage(initialFarmId = 12) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/farms/${initialFarmId}/environment`]}>
        <Routes>
          <Route path="/farms/:farmId/environment" element={<EnvironmentalDashboardPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  mocks.getFarm.mockResolvedValue(farm())
  mocks.listFarms.mockResolvedValue({ count: 1, next: null, previous: null, results: [farm()] })
  mocks.summary.mockResolvedValue(summary())
  mocks.scan.mockResolvedValue({
    status: 'QUEUED',
    farm_id: 12,
    job_id: 'job-1',
    task_id: 'task-1',
    start: '2025-11-15',
    end: '2026-11-11',
    parameters: ['T2M', 'PRECTOTCORR'],
    status_url: '/api/v1/data-jobs/job-1/',
  })
  mocks.job.mockResolvedValue(dataJob())
})

afterEach(cleanup)

describe('EnvironmentalDashboardPage', () => {
  it('shows a loading state while the summary is being read', async () => {
    mocks.summary.mockReturnValue(new Promise(() => {}))
    renderPage()

    expect(await screen.findByText('Reading environmental summary…')).toBeTruthy()
  })

  it('renders the four indicators, real measurements, sources and freshness', async () => {
    renderPage()

    expect(
      await screen.findByRole('heading', { name: 'What the stored observations show' }),
    ).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Water' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Heat' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Soil' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Market' })).toBeTruthy()

    expect(screen.getAllByText('12.4 mm').length).toBeGreaterThan(0)
    expect(screen.getByText('19.2 C')).toBeTruthy()
    expect(screen.getByText('7.2 pH')).toBeTruthy()
    expect(screen.getAllByText('NASA POWER').length).toBeGreaterThan(0)
    expect(screen.getAllByText('MERRA-2').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/0.5 x 0.625 degree grid/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Recent').length).toBeGreaterThan(0)
    expect(screen.getAllByText('30 of 30 days observed').length).toBeGreaterThan(0)
    expect(screen.getByText('2 of 6 properties recorded')).toBeTruthy()
    expect(screen.getAllByText(/not on-farm measurements/).length).toBeGreaterThan(0)
  })

  it('keeps a partial response partial and shows the missing inputs', async () => {
    mocks.summary.mockResolvedValue(
      summary({
        data_status: 'PARTIAL',
        indicators: {
          ...summary().indicators,
          water: indicator({
            status: 'PARTIAL',
            summary: '24 of 30 days observed: 8.1 mm of rainfall over covered days.',
            coverage: {
              days_expected: 30,
              days_covered: 24,
              days_missing: 6,
              ratio: '0.8000',
              by_parameter: { PRECTOTCORR: 24 },
            },
            missing: [
              {
                name: 'soil_moisture',
                impact: 'Plant-available water and water stress cannot be assessed.',
                required_for: 'water stress',
              },
            ],
          }),
        },
      }),
    )
    renderPage()

    expect(await screen.findByText('24 of 30 days observed · 6 missing')).toBeTruthy()
    expect(screen.getByText('soil moisture')).toBeTruthy()
    expect(screen.getAllByText('Partial').length).toBeGreaterThan(0)
  })

  it('never renders a missing value as zero', async () => {
    mocks.summary.mockResolvedValue(
      summary({
        data_status: 'INSUFFICIENT_DATA',
        indicators: {
          ...summary().indicators,
          heat: indicator({
            code: 'HEAT',
            label: 'Heat',
            status: 'INSUFFICIENT_DATA',
            confidence: 'NONE',
            summary: 'No temperature observation is available in this window.',
            measurements: [
              measurement({
                name: 'mean_temperature',
                value: null,
                unit: 'C',
                parameter: 'T2M',
              }),
            ],
          }),
        },
      }),
    )
    renderPage()

    expect(await screen.findByText('No temperature observation is available in this window.')).toBeTruthy()
    expect(screen.getAllByText('Not available').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Insufficient data').length).toBeGreaterThan(0)
    expect(screen.queryByText(/^0 mm$/)).toBeNull()
  })

  it('labels stale observations as stale', async () => {
    const stale = summary()
    mocks.summary.mockResolvedValue(
      summary({
        freshness: { ...stale.freshness, status: 'STALE' },
        window: { ...stale.window, freshness: 'STALE' },
        indicators: {
          ...stale.indicators,
          water: indicator({
            period: {
              start: '2025-08-01',
              end: '2025-08-30',
              latest_observation: '2025-08-30',
              age_days: 441,
              freshness: 'STALE',
            },
          }),
        },
      }),
    )
    renderPage()

    expect((await screen.findAllByText('Stale')).length).toBeGreaterThan(0)
    expect(screen.getByText(/441 day\(s\) old/)).toBeTruthy()
  })

  it('keeps MARKET unavailable and shows no invented price', async () => {
    renderPage()

    expect(await screen.findByText(/No verified local market price source/)).toBeTruthy()
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/No measurement values are reported/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/EGP/)).toBeNull()
  })

  it('requests a scan through the documented API and shows queued progress', async () => {
    renderPage()
    const user = userEvent.setup()

    await screen.findByRole('heading', { name: 'What the stored observations show' })
    await user.click(screen.getByRole('button', { name: 'Request NASA POWER scan' }))

    await waitFor(() => expect(mocks.scan).toHaveBeenCalledWith(12, {}))
    expect(await screen.findByText('Scan running')).toBeTruthy()
    expect(screen.getByText('Running')).toBeTruthy()
    expect(
      (screen.getByRole('button', { name: 'Scan in progress…' }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('refreshes the summary after a successful scan and reports the stored days', async () => {
    mocks.job.mockResolvedValue(
      dataJob({
        status: 'SUCCEEDED',
        days_stored: 365,
        days_missing: 0,
        finished_at: '2026-11-14T10:05:00Z',
        duration_ms: 295000,
      }),
    )
    renderPage()
    const user = userEvent.setup()

    await screen.findByRole('heading', { name: 'What the stored observations show' })
    await user.click(screen.getByRole('button', { name: 'Request NASA POWER scan' }))

    expect(await screen.findByText(/The scan finished/)).toBeTruthy()
    expect(screen.getByText('Succeeded')).toBeTruthy()
    expect(screen.getAllByText('365').length).toBeGreaterThan(0)
    await waitFor(() => expect(mocks.summary).toHaveBeenCalledTimes(2))
  })

  it('reports a failed scan without claiming new observations', async () => {
    mocks.job.mockResolvedValue(
      dataJob({
        status: 'FAILED',
        error_code: 'PROVIDER_429',
        error_message: 'NASA POWER rate limit reached.',
        days_stored: 0,
        days_missing: 365,
        finished_at: '2026-11-14T10:01:00Z',
      }),
    )
    renderPage()
    const user = userEvent.setup()

    await screen.findByRole('heading', { name: 'What the stored observations show' })
    await user.click(screen.getByRole('button', { name: 'Request NASA POWER scan' }))

    expect(await screen.findByText(/NASA POWER rate limit reached/)).toBeTruthy()
    expect(screen.getByText('Failed')).toBeTruthy()
    expect(screen.queryByText(/The scan finished/)).toBeNull()
    expect(mocks.summary).toHaveBeenCalledTimes(1)
  })

  it('surfaces a network failure instead of demo data', async () => {
    mocks.summary.mockRejectedValue(
      new ApiError('Cannot reach the Overfield API at http://127.0.0.1:8000.'),
    )
    renderPage()

    expect(await screen.findByText('Could not load the environmental summary')).toBeTruthy()
    expect(screen.getByText(/Cannot reach the Overfield API/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Request NASA POWER scan' })).toBeTruthy()
  })

  it('reports an expired session and hides scan controls', async () => {
    mocks.summary.mockRejectedValue(
      new ApiError('Your session has expired. Please sign in again.', 401),
    )
    renderPage()

    expect(await screen.findByText('Environmental summary unavailable')).toBeTruthy()
    expect(screen.getAllByText(/session has expired/).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: 'Request NASA POWER scan' })).toBeNull()
  })

  it('switches farms through the selector and reloads the summary', async () => {
    mocks.getFarm.mockImplementation((farmId: number) =>
      Promise.resolve(farm(farmId, farmId === 12 ? 'Alpha farm' : 'Beta farm')),
    )
    mocks.listFarms.mockResolvedValue({
      count: 2,
      next: null,
      previous: null,
      results: [farm(12, 'Alpha farm'), farm(2, 'Beta farm')],
    })
    mocks.summary.mockImplementation((farmId: number) =>
      Promise.resolve(summary({ farm_id: farmId, indicators: summary().indicators })),
    )
    renderPage(12)
    const user = userEvent.setup()

    expect(await screen.findByRole('heading', { name: 'Alpha farm' })).toBeTruthy()
    await user.selectOptions(screen.getByLabelText('Switch farm'), '2')

    await waitFor(() => expect(mocks.summary).toHaveBeenCalledWith(2, 30))
    expect(await screen.findByRole('heading', { name: 'Beta farm' })).toBeTruthy()
  })
})
