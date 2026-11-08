import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createFarm, saveFarmContext } from '../api/farms'
import { ApiError } from '../api/types'
import { useAuth } from '../auth/auth-context'
import { Banner } from '../components/Field'
import { Stepper } from '../components/Stepper'
import { clearDraft, clearStep, loadDraft, loadStep, saveDraft, saveStep } from '../lib/draftStore'
import {
  applyProfileDefaults,
  buildContextPayload,
  buildFarmCreatePayload,
  createEmptyDraft,
  validateBoundary,
  validateFarmDetails,
  validateProfile,
  type OnboardingDraft,
} from '../lib/onboarding'
import { BoundaryStep } from '../onboarding/BoundaryStep'
import { FarmDetailsStep } from '../onboarding/FarmDetailsStep'
import { FarmInfoStep } from '../onboarding/FarmInfoStep'
import { ProfileStep } from '../onboarding/ProfileStep'
import { ReviewStep } from '../onboarding/ReviewStep'

const STEPS = [
  { id: 'profile', label: 'Profile' },
  { id: 'details', label: 'Farm' },
  { id: 'boundary', label: 'Boundary' },
  { id: 'info', label: 'Details' },
  { id: 'review', label: 'Review' },
]

const VALIDATORS = [validateProfile, validateFarmDetails, validateBoundary, () => ({}), () => ({})]

export function OnboardingPage() {
  const { profile, updateProfile } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [draft, setDraft] = useState<OnboardingDraft>(() => {
    const base = loadDraft() ?? createEmptyDraft()
    return profile ? applyProfileDefaults(base, profile) : base
  })
  const [step, setStep] = useState(() => loadStep())
  const [maxStep, setMaxStep] = useState(() => loadStep())
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [savingProfile, setSavingProfile] = useState(false)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [backendFieldErrors, setBackendFieldErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    saveDraft(draft)
  }, [draft])

  useEffect(() => {
    saveStep(step)
  }, [step])

  const patch = useCallback((updates: Partial<OnboardingDraft>) => {
    setDraft((current) => ({ ...current, ...updates }))
  }, [])

  const goTo = (target: number) => {
    setErrors({})
    setStep(target)
    setMaxStep((current) => Math.max(current, target))
  }

  const handleNext = async () => {
    const stepErrors = VALIDATORS[step](draft)
    setErrors(stepErrors)
    if (Object.keys(stepErrors).length > 0) return

    if (step === 0) {
      setSavingProfile(true)
      try {
        await updateProfile({
          display_name: draft.profile.displayName,
          email: draft.profile.email,
          preferred_language: draft.profile.preferredLanguage,
        })
      } catch (caught) {
        if (caught instanceof ApiError) {
          setErrors(caught.fieldMessages)
        }
        setErrors((current) => ({
          ...current,
          profile: caught instanceof ApiError ? caught.message : 'Could not save your profile.',
        }))
        return
      } finally {
        setSavingProfile(false)
      }
    }

    goTo(Math.min(step + 1, STEPS.length - 1))
  }

  const handleSave = async () => {
    setSaving(true)
    setSaveError(null)
    setBackendFieldErrors({})
    try {
      const farm = await createFarm(buildFarmCreatePayload(draft))
      let contextError: string | null = null
      try {
        await saveFarmContext(farm.id, buildContextPayload(draft))
      } catch (caught) {
        contextError =
          caught instanceof ApiError ? caught.message : 'Farm information could not be saved.'
      }
      await queryClient.invalidateQueries({ queryKey: ['farms'] })
      clearDraft()
      clearStep()
      navigate(`/farms/${farm.id}`, { state: { contextError } })
    } catch (caught) {
      if (caught instanceof ApiError) {
        setSaveError(caught.message)
        setBackendFieldErrors(caught.fieldMessages)
      } else {
        setSaveError('The farm could not be saved. Please try again.')
      }
    } finally {
      setSaving(false)
    }
  }

  const stepContent = (() => {
    switch (step) {
      case 0:
        return <ProfileStep draft={draft} errors={errors} onChange={patch} />
      case 1:
        return <FarmDetailsStep draft={draft} errors={errors} onChange={patch} />
      case 2:
        return <BoundaryStep draft={draft} errors={errors} onChange={patch} />
      case 3:
        return <FarmInfoStep draft={draft} errors={errors} onChange={patch} />
      default:
        return (
          <ReviewStep
            draft={draft}
            onEdit={goTo}
            onSave={() => void handleSave()}
            saving={saving}
            saveError={saveError}
            backendFieldErrors={backendFieldErrors}
          />
        )
    }
  })()

  return (
    <div className="page onboarding">
      <header className="page-header">
        <div>
          <p className="step-kicker">Farm onboarding</p>
          <h2 className="page-title">Add a farm</h2>
          <p className="page-lead">
            Five short steps. Your progress is kept in this tab if you need to pause.
          </p>
        </div>
      </header>

      <Stepper steps={STEPS} current={step} maxReached={maxStep} onSelect={goTo} />

      {errors.profile ? <Banner tone="error">{errors.profile}</Banner> : null}

      {stepContent}

      {step < STEPS.length - 1 ? (
        <div className="wizard-actions">
          <button
            type="button"
            className="button button-ghost"
            onClick={() => goTo(Math.max(0, step - 1))}
            disabled={step === 0 || savingProfile}
          >
            Back
          </button>
          <button
            type="button"
            className="button button-primary"
            onClick={() => void handleNext()}
            disabled={savingProfile}
          >
            {savingProfile ? 'Saving profile…' : step === 2 ? 'Continue' : 'Next'}
          </button>
        </div>
      ) : null}
    </div>
  )
}
