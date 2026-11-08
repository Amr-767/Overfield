// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuth } from './auth-context'
import { AuthProvider } from './AuthProvider'

const requestTokenPairMock = vi.fn()

vi.mock('../api/auth', () => ({
  fetchProfile: vi.fn().mockResolvedValue({
    username: 'farmerA',
    display_name: 'Farmer A',
    email: 'a@example.com',
    preferred_language: 'en',
  }),
  requestTokenPair: (...args: unknown[]) => requestTokenPairMock(...args),
  refreshAccessToken: vi.fn(),
  registerFarmer: vi.fn(),
  updateProfile: vi.fn(),
}))

function Probe() {
  const { status, logout, login } = useAuth()
  return (
    <div>
      <span data-testid="status">{status}</span>
      <button type="button" onClick={logout}>
        logout
      </button>
      <button type="button" onClick={() => void login('farmerA', 'secret123')}>
        login
      </button>
    </div>
  )
}

function renderProvider() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  )
  return queryClient
}

const previousUserFarms = { count: 1, next: null, previous: null, results: [{ id: 99 }] }

beforeEach(() => {
  window.sessionStorage.clear()
  requestTokenPairMock.mockReset().mockResolvedValue({ access: 'a', refresh: 'r' })
})

afterEach(cleanup)

describe('AuthProvider identity transitions', () => {
  it('clears cached queries and onboarding state on logout', async () => {
    const queryClient = renderProvider()
    queryClient.setQueryData(['farms'], previousUserFarms)
    window.sessionStorage.setItem('agrospace.onboarding.draft', '{"farm":{"name":"Secret"}}')
    window.sessionStorage.setItem('agrospace.onboarding.step', '3')

    await userEvent.click(screen.getByRole('button', { name: 'logout' }))

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('anonymous'))
    // A second farmer must never see the previous account's cached farms.
    expect(queryClient.getQueryData(['farms'])).toBeUndefined()
    expect(window.sessionStorage.getItem('agrospace.onboarding.draft')).toBeNull()
    expect(window.sessionStorage.getItem('agrospace.onboarding.step')).toBeNull()
  })

  it('clears cached queries when a different account signs in', async () => {
    const queryClient = renderProvider()
    queryClient.setQueryData(['farms'], previousUserFarms)

    await userEvent.click(screen.getByRole('button', { name: 'login' }))

    await waitFor(() => expect(screen.getByTestId('status').textContent).toBe('authenticated'))
    expect(requestTokenPairMock).toHaveBeenCalledWith('farmerA', 'secret123')
    expect(queryClient.getQueryData(['farms'])).toBeUndefined()
  })
})
