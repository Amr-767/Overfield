import { createContext, useContext } from 'react'

import type { Profile, RegisterPayload } from '../api/types'

export type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

export interface AuthState {
  status: AuthStatus
  profile: Profile | null
}

export interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<void>
  register: (payload: RegisterPayload) => Promise<void>
  logout: () => void
  refreshProfile: () => Promise<void>
  updateProfile: (payload: {
    display_name?: string
    preferred_language?: string
    email?: string
  }) => Promise<Profile>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside <AuthProvider>.')
  }
  return context
}
