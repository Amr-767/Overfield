import type { OnboardingDraft } from '../lib/onboarding'
import { Field } from '../components/Field'

interface StepProps {
  draft: OnboardingDraft
  errors: Record<string, string>
  onChange: (patch: Partial<OnboardingDraft>) => void
}

export function ProfileStep({ draft, errors, onChange }: StepProps) {
  const { profile } = draft

  return (
    <section className="step-panel" aria-labelledby="profile-step-title">
      <header className="step-header">
        <p className="step-kicker">Step 1 of 5</p>
        <h2 id="profile-step-title">Your farmer profile</h2>
        <p className="step-lead">
          This is how your farms are identified. You can change any of it later.
        </p>
      </header>

      <div className="form-grid">
        <Field
          id="display-name"
          label="What should we call you?"
          hint="Your name or your farm's name — whatever is easiest to recognise."
          optional
          error={errors.displayName}
        >
          <input
            id="display-name"
            className="input"
            value={profile.displayName}
            maxLength={120}
            autoComplete="name"
            onChange={(event) => onChange({ profile: { ...profile, displayName: event.target.value } })}
          />
        </Field>

        <Field
          id="profile-email"
          label="Email address"
          hint="Used only for your account. You can leave it empty."
          optional
          error={errors.email}
        >
          <input
            id="profile-email"
            className="input"
            type="email"
            value={profile.email}
            autoComplete="email"
            onChange={(event) => onChange({ profile: { ...profile, email: event.target.value } })}
          />
        </Field>

        <Field id="preferred-language" label="Preferred language" optional>
          <select
            id="preferred-language"
            className="input"
            value={profile.preferredLanguage}
            onChange={(event) =>
              onChange({ profile: { ...profile, preferredLanguage: event.target.value } })
            }
          >
            <option value="en">English</option>
            <option value="ar">العربية</option>
          </select>
        </Field>
      </div>
    </section>
  )
}
