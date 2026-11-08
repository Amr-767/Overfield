import { createEmptyDraft, mergeDraft, type OnboardingDraft } from './onboarding'

const DRAFT_KEY = 'agrospace.onboarding.draft'
const STEP_KEY = 'agrospace.onboarding.step'
const MAX_STEP = 4

/** Restore an in-progress onboarding draft for this tab. */
export function loadDraft(): OnboardingDraft | null {
  try {
    const raw = window.sessionStorage.getItem(DRAFT_KEY)
    if (!raw) return null
    return mergeDraft(createEmptyDraft(), JSON.parse(raw))
  } catch {
    return null
  }
}

export function saveDraft(draft: OnboardingDraft): void {
  try {
    window.sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
  } catch {
    // Draft persistence is best-effort (private browsing can block storage).
  }
}

export function clearDraft(): void {
  try {
    window.sessionStorage.removeItem(DRAFT_KEY)
  } catch {
    // Ignore.
  }
}

/** Restore the step the farmer was on (so a reload resumes in place). */
export function loadStep(): number {
  try {
    const raw = window.sessionStorage.getItem(STEP_KEY)
    if (raw === null) return 0
    const step = Number(raw)
    return Number.isInteger(step) && step >= 0 && step <= MAX_STEP ? step : 0
  } catch {
    return 0
  }
}

export function saveStep(step: number): void {
  try {
    window.sessionStorage.setItem(STEP_KEY, String(step))
  } catch {
    // Ignore.
  }
}

export function clearStep(): void {
  try {
    window.sessionStorage.removeItem(STEP_KEY)
  } catch {
    // Ignore.
  }
}
