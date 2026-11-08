// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, type BoundaryGeometry, type Farm } from '../api/types'

const POLYGON: BoundaryGeometry = {
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

const createFarmMock = vi.fn()
const saveFarmContextMock = vi.fn()
const validateBoundaryMock = vi.fn()
const updateProfileMock = vi.fn()

vi.mock('../api/farms', () => ({
  createFarm: (...args: unknown[]) => createFarmMock(...args),
  saveFarmContext: (...args: unknown[]) => saveFarmContextMock(...args),
  validateBoundary: (...args: unknown[]) => validateBoundaryMock(...args),
}))

vi.mock('../auth/auth-context', () => ({
  useAuth: () => ({
    status: 'authenticated',
    profile: {
      username: 'farmer1',
      display_name: 'Ahmed',
      email: 'farmer1@example.com',
      preferred_language: 'en',
    },
    updateProfile: updateProfileMock,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refreshProfile: vi.fn(),
  }),
}))

// The real map needs a browser layout engine; the stub still exercises the
// boundary callback used by the step.
vi.mock('../components/FarmMap', () => ({
  FarmMap: ({ onBoundaryChange }: { onBoundaryChange?: (g: BoundaryGeometry) => void }) => (
    <button type="button" onClick={() => onBoundaryChange?.(POLYGON)}>
      stub-draw-boundary
    </button>
  ),
}))

import { OnboardingPage } from './OnboardingPage'

const savedFarm: Farm = {
  id: 7,
  name: 'North Field',
  country_code: 'EG',
  region_code: 'Gharbia',
  boundary: { type: 'MultiPolygon', coordinates: [POLYGON.coordinates as number[][][]] },
  location: { type: 'Point', coordinates: [30.95115, 30.79095] },
  area_hectares: '3.7882',
  area_source: 'GEOMETRY_DERIVED',
  geometry_source: 'BOUNDARY',
  spatial_precision: 'HIGH',
  timezone: 'Africa/Cairo',
  zone_count: 0,
  created_at: '2026-11-07T12:00:00Z',
  updated_at: '2026-11-07T12:00:00Z',
}

function renderWizard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/onboarding']}>
        <Routes>
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/farms/:farmId" element={<p>farm detail page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  window.sessionStorage.clear()
  createFarmMock.mockReset().mockResolvedValue(savedFarm)
  saveFarmContextMock.mockReset().mockResolvedValue({})
  validateBoundaryMock.mockReset().mockResolvedValue({
    valid: true,
    srid: 4326,
    area_hectares: '3.7882',
    area_method: 'postgis_geography',
    geometry: savedFarm.boundary,
  })
  updateProfileMock.mockReset().mockResolvedValue({})
})

afterEach(cleanup)

async function completeFarmDetails() {
  await userEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Farm details' })).toBeTruthy())
  await userEvent.type(screen.getByLabelText('Farm name'), 'North Field')
  await userEvent.click(screen.getByRole('button', { name: 'Next' }))
  await waitFor(() => expect(screen.getByRole('heading', { name: 'Draw your farm' })).toBeTruthy())
}

describe('OnboardingPage', () => {
  it('validates the farm name before continuing', async () => {
    renderWizard()
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Farm details' })).toBeTruthy())

    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(await screen.findByText(/give your farm a name/i)).toBeTruthy()
    // Still on the same step.
    expect(screen.getByRole('heading', { name: 'Farm details' })).toBeTruthy()
  })

  it('saves the farm and the context with the drawn GeoJSON', async () => {
    renderWizard()
    await completeFarmDetails()

    await userEvent.click(screen.getByRole('button', { name: 'stub-draw-boundary' }))
    await waitFor(() => expect(validateBoundaryMock).toHaveBeenCalled())
    await waitFor(() =>
      expect(screen.getByText(/calculated from your boundary/i)).toBeTruthy(),
    )

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'A little about your farm' })).toBeTruthy(),
    )

    // Farm information is optional: continue without filling anything.
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Review and save' })).toBeTruthy(),
    )
    expect(screen.getByText('3.79 ha')).toBeTruthy()

    await userEvent.click(screen.getByRole('button', { name: 'Save farm' }))

    await waitFor(() => expect(createFarmMock).toHaveBeenCalledTimes(1))
    const payload = createFarmMock.mock.calls[0][0]
    expect(payload.name).toBe('North Field')
    expect(payload.boundary).toEqual(POLYGON)
    expect(payload.farmer_reported_area_hectares).toBeUndefined()

    await waitFor(() => expect(saveFarmContextMock).toHaveBeenCalledWith(7, expect.anything()))
    expect(await screen.findByText('farm detail page')).toBeTruthy()
    // Drafts are cleared only after a successful save.
    expect(window.sessionStorage.getItem('agrospace.onboarding.draft')).toBeNull()
  })

  it('shows backend validation errors on the review step', async () => {
    createFarmMock.mockRejectedValueOnce(
      new ApiError('Invalid polygon: geometry is not closed.', 400, {
        boundary: ['Invalid polygon: geometry is not closed.'],
      }),
    )

    renderWizard()
    await completeFarmDetails()
    await userEvent.click(screen.getByRole('button', { name: 'stub-draw-boundary' }))
    await waitFor(() => expect(validateBoundaryMock).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: 'Continue' }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'A little about your farm' })).toBeTruthy(),
    )
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Review and save' })).toBeTruthy(),
    )

    await userEvent.click(screen.getByRole('button', { name: 'Save farm' }))

    expect(await screen.findByText(/could not save this farm/i)).toBeTruthy()
    expect(screen.getAllByText(/geometry is not closed/i).length).toBeGreaterThan(0)
    // The farmer stays on review to correct the problem.
    expect(screen.getByRole('heading', { name: 'Review and save' })).toBeTruthy()
  })

  it('keeps the draft when the page is re-rendered', async () => {
    const first = renderWizard()
    await userEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Farm details' })).toBeTruthy())
    await userEvent.type(screen.getByLabelText('Farm name'), 'Stored Field')

    await waitFor(() => {
      const raw = window.sessionStorage.getItem('agrospace.onboarding.draft')
      expect(raw).toBeTruthy()
      expect(JSON.parse(raw as string).farm.name).toBe('Stored Field')
    })

    first.unmount()
    renderWizard()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Farm details' })).toBeTruthy())
    expect((screen.getByLabelText('Farm name') as HTMLInputElement).value).toBe('Stored Field')
  })
})
