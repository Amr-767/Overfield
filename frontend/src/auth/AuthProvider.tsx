import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  fetchProfile,
  refreshAccessToken,
  registerFarmer,
  requestTokenPair,
  updateProfile as updateProfileApi,
  type ProfileUpdatePayload,
} from '../api/auth'
import { setAccessToken, setUnauthorizedHandler } from '../api/client'
import type { Profile, RegisterPayload, TokenPair } from '../api/types'
import { clearDraft, clearStep } from '../lib/draftStore'
import { AuthContext, type AuthState } from './auth-context'
import { clearRefreshToken, loadRefreshToken, saveRefreshToken } from './tokenStore'

const anonymous: AuthState = { status: 'anonymous', profile: null }
const loading: AuthState = { status: 'loading', profile: null }

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const [state, setState] = useState<AuthState>(() =>
    loadRefreshToken() ? loading : anonymous,
  )

  const applyTokens = useCallback((tokens: TokenPair) => {
    setAccessToken(tokens.access)
    saveRefreshToken(tokens.refresh)
  }, [])

  /**
   * Drop every piece of state that belongs to the previous identity.
   *
   * The React Query cache is keyed by resource only (e.g. `['farms']`), so
   * without this an account switch would serve the previous farmer's cached
   * farms to the next user signing in on the same browser.
   */
  const forgetSession = useCallback(() => {
    setAccessToken(null)
    clearRefreshToken()
    queryClient.clear()
    clearDraft()
    clearStep()
    setState(anonymous)
  }, [queryClient])

  // Restore the session from the refresh token on first load so a page reload
  // does not sign the farmer out.
  useEffect(() => {
    const refresh = loadRefreshToken()
    if (!refresh) return

    let cancelled = false
    const bootstrap = async () => {
      try {
        const { access } = await refreshAccessToken(refresh)
        if (cancelled) return
        setAccessToken(access)
        const profile = await fetchProfile()
        if (!cancelled) setState({ status: 'authenticated', profile })
      } catch {
        if (!cancelled) forgetSession()
      }
    }
    void bootstrap()

    return () => {
      cancelled = true
    }
  }, [forgetSession])

  // Transparent single retry when the short-lived access token expires.
  useEffect(() => {
    setUnauthorizedHandler(async () => {
      const refresh = loadRefreshToken()
      if (!refresh) {
        forgetSession()
        return false
      }
      try {
        const { access } = await refreshAccessToken(refresh)
        setAccessToken(access)
        return true
      } catch {
        forgetSession()
        return false
      }
    })
    return () => setUnauthorizedHandler(null)
  }, [forgetSession])

  const login = useCallback(
    async (username: string, password: string) => {
      const tokens = await requestTokenPair(username, password)
      applyTokens(tokens)
      const profile = await fetchProfile()
      queryClient.clear()
      setState({ status: 'authenticated', profile })
    },
    [applyTokens, queryClient],
  )

  const register = useCallback(
    async (payload: RegisterPayload) => {
      await registerFarmer(payload)
      const tokens = await requestTokenPair(payload.username, payload.password)
      applyTokens(tokens)
      const profile = await fetchProfile()
      queryClient.clear()
      setState({ status: 'authenticated', profile })
    },
    [applyTokens, queryClient],
  )

  const refreshProfile = useCallback(async () => {
    const profile = await fetchProfile()
    setState({ status: 'authenticated', profile })
  }, [])

  const updateProfile = useCallback(async (payload: ProfileUpdatePayload): Promise<Profile> => {
    const profile = await updateProfileApi(payload)
    setState({ status: 'authenticated', profile })
    return profile
  }, [])

  const value = useMemo(
    () => ({
      ...state,
      login,
      register,
      logout: forgetSession,
      refreshProfile,
      updateProfile,
    }),
    [state, login, register, forgetSession, refreshProfile, updateProfile],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
