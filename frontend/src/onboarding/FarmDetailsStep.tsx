import { Field } from '../components/Field'
import type { OnboardingDraft } from '../lib/onboarding'

interface StepProps {
  draft: OnboardingDraft
  errors: Record<string, string>
  onChange: (patch: Partial<OnboardingDraft>) => void
}

const TIMEZONES = [
  { value: 'Africa/Cairo', label: 'Africa/Cairo (Egypt)' },
  { value: 'Africa/Khartoum', label: 'Africa/Khartoum (Sudan)' },
  { value: 'Africa/Nairobi', label: 'Africa/Nairobi (East Africa)' },
  { value: 'Asia/Riyadh', label: 'Asia/Riyadh (Arabian Peninsula)' },
  { value: 'UTC', label: 'UTC' },
]

export function FarmDetailsStep({ draft, errors, onChange }: StepProps) {
  const { farm } = draft
  const patchFarm = (patch: Partial<OnboardingDraft['farm']>) =>
    onChange({ farm: { ...farm, ...patch } })

  return (
    <section className="step-panel" aria-labelledby="farm-step-title">
      <header className="step-header">
        <p className="step-kicker">Step 2 of 5</p>
        <h2 id="farm-step-title">Farm details</h2>
        <p className="step-lead">Name your farm and tell us roughly where it is.</p>
      </header>

      <div className="form-grid">
        <Field
          id="farm-name"
          label="Farm name"
          hint="For example: North field, Home plot, Gharbia block A."
          error={errors.name}
        >
          <input
            id="farm-name"
            className="input"
            value={farm.name}
            maxLength={120}
            placeholder="North field"
            onChange={(event) => patchFarm({ name: event.target.value })}
          />
        </Field>

        <div className="form-row">
          <Field
            id="country-code"
            label="Country"
            hint="Two-letter code, e.g. EG for Egypt."
            error={errors.countryCode}
          >
            <input
              id="country-code"
              className="input input-code"
              value={farm.countryCode}
              maxLength={2}
              placeholder="EG"
              onChange={(event) => patchFarm({ countryCode: event.target.value.toUpperCase() })}
            />
          </Field>

          <Field
            id="region-code"
            label="Region"
            hint="Governorate, district or any label you use locally."
            optional
            error={errors.regionCode}
          >
            <input
              id="region-code"
              className="input"
              value={farm.regionCode}
              maxLength={80}
              placeholder="Gharbia"
              onChange={(event) => patchFarm({ regionCode: event.target.value })}
            />
          </Field>
        </div>

        <Field
          id="timezone"
          label="Timezone"
          hint="Used when farm data is dated."
          error={errors.timezone}
        >
          <input
            id="timezone"
            className="input"
            list="timezone-options"
            value={farm.timezone}
            onChange={(event) => patchFarm({ timezone: event.target.value })}
          />
          <datalist id="timezone-options">
            {TIMEZONES.map((zone) => (
              <option key={zone.value} value={zone.value}>
                {zone.label}
              </option>
            ))}
          </datalist>
        </Field>
      </div>
    </section>
  )
}
