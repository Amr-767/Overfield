// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { clearDraft, loadDraft, saveDraft } from './draftStore'
import { createEmptyDraft } from './onboarding'

beforeEach(() => {
  window.sessionStorage.clear()
})

afterEach(() => {
  window.sessionStorage.clear()
})

describe('onboarding draft persistence', () => {
  it('returns null when no draft is stored', () => {
    expect(loadDraft()).toBeNull()
  })

  it('round-trips a draft through sessionStorage', () => {
    const draft = createEmptyDraft()
    draft.farm.name = 'Delta plot'
    draft.mode = 'point'
    draft.reportedAreaHa = '4.2'

    saveDraft(draft)
    const restored = loadDraft()

    expect(restored?.farm.name).toBe('Delta plot')
    expect(restored?.mode).toBe('point')
    expect(restored?.reportedAreaHa).toBe('4.2')
  })

  it('fills defaults for keys missing from an older stored draft', () => {
    window.sessionStorage.setItem(
      'agrospace.onboarding.draft',
      JSON.stringify({ farm: { name: 'Legacy' } }),
    )
    const restored = loadDraft()
    expect(restored?.farm.name).toBe('Legacy')
    expect(restored?.farm.timezone).toBe('Africa/Cairo')
    expect(restored?.profile.preferredLanguage).toBe('en')
  })

  it('ignores corrupt JSON instead of throwing', () => {
    window.sessionStorage.setItem('agrospace.onboarding.draft', 'not-json{')
    expect(loadDraft()).toBeNull()
  })

  it('clears a stored draft', () => {
    saveDraft(createEmptyDraft())
    clearDraft()
    expect(loadDraft()).toBeNull()
  })
})
