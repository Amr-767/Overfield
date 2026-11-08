import { useState } from 'react'

import { Banner, Field } from '../components/Field'
import {
  IRRIGATION_OPTIONS,
  PRIORITY_FIELDS,
  RELIABILITY_OPTIONS,
  SEED_OPTIONS,
  SOIL_SOURCES,
  TEXTURE_OPTIONS,
  normalizePriorities,
  type OnboardingDraft,
} from '../lib/onboarding'

interface StepProps {
  draft: OnboardingDraft
  errors: Record<string, string>
  onChange: (patch: Partial<OnboardingDraft>) => void
}

export function FarmInfoStep({ draft, errors, onChange }: StepProps) {
  const [showNutrients, setShowNutrients] = useState(false)
  const { soil, water, crops, constraints, priorities } = draft

  const patchSoil = (patch: Partial<OnboardingDraft['soil']>) =>
    onChange({ soil: { ...soil, ...patch } })
  const patchWater = (patch: Partial<OnboardingDraft['water']>) =>
    onChange({ water: { ...water, ...patch } })
  const patchConstraints = (patch: Partial<OnboardingDraft['constraints']>) =>
    onChange({ constraints: { ...constraints, ...patch } })

  const updateCrop = (index: number, patch: Partial<OnboardingDraft['crops'][number]>) => {
    const next = crops.map((entry, entryIndex) =>
      entryIndex === index ? { ...entry, ...patch } : entry,
    )
    onChange({ crops: next })
  }

  const weights = normalizePriorities(priorities)

  return (
    <section className="step-panel" aria-labelledby="info-step-title">
      <header className="step-header">
        <p className="step-kicker">Step 4 of 5</p>
        <h2 id="info-step-title">A little about your farm</h2>
        <p className="step-lead">
          Everything here is optional. Skip anything you are not sure about — we will not guess
          values for you.
        </p>
      </header>

      <div className="info-block">
        <h3>Soil</h3>
        <div className="form-grid">
          <Field id="soil-source" label="Where does this soil information come from?" optional>
            <select
              id="soil-source"
              className="input"
              value={soil.source}
              onChange={(event) =>
                patchSoil({ source: event.target.value as OnboardingDraft['soil']['source'] })
              }
            >
              {SOIL_SOURCES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="soil-texture" label="Soil type" optional>
            <select
              id="soil-texture"
              className="input"
              value={soil.textureClass}
              onChange={(event) => patchSoil({ textureClass: event.target.value })}
            >
              {TEXTURE_OPTIONS.map((option) => (
                <option key={`${option.value}::${option.label}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <div className="form-row">
            <Field id="soil-ph" label="Soil pH" hint="0–14, if you know it." optional error={errors.ph}>
              <input
                id="soil-ph"
                className="input input-narrow"
                inputMode="decimal"
                value={soil.ph}
                placeholder="7.5"
                onChange={(event) => patchSoil({ ph: event.target.value })}
              />
            </Field>
            <Field id="soil-lab" label="Lab or test name" optional>
              <input
                id="soil-lab"
                className="input"
                value={soil.labName}
                placeholder="Delta Soil Lab"
                onChange={(event) => patchSoil({ labName: event.target.value })}
              />
            </Field>
          </div>

          <div>
            <button
              type="button"
              className="button button-ghost"
              aria-expanded={showNutrients}
              onClick={() => setShowNutrients((value) => !value)}
            >
              {showNutrients ? 'Hide soil test details' : 'Add soil test details'}
            </button>
          </div>

          {showNutrients ? (
            <div className="subpanel">
              <div className="form-row">
                <Field id="soil-n" label="Nitrogen (ppm)" optional>
                  <input
                    id="soil-n"
                    className="input input-narrow"
                    inputMode="decimal"
                    value={soil.nitrogen}
                    onChange={(event) => patchSoil({ nitrogen: event.target.value })}
                  />
                </Field>
                <Field id="soil-p" label="Phosphorus (ppm)" optional>
                  <input
                    id="soil-p"
                    className="input input-narrow"
                    inputMode="decimal"
                    value={soil.phosphorus}
                    onChange={(event) => patchSoil({ phosphorus: event.target.value })}
                  />
                </Field>
                <Field id="soil-k" label="Potassium (ppm)" optional>
                  <input
                    id="soil-k"
                    className="input input-narrow"
                    inputMode="decimal"
                    value={soil.potassium}
                    onChange={(event) => patchSoil({ potassium: event.target.value })}
                  />
                </Field>
              </div>
              <div className="form-row">
                <Field id="soil-oc" label="Organic carbon (%)" optional>
                  <input
                    id="soil-oc"
                    className="input input-narrow"
                    inputMode="decimal"
                    value={soil.organicCarbon}
                    onChange={(event) => patchSoil({ organicCarbon: event.target.value })}
                  />
                </Field>
                <Field id="soil-depth" label="Sample depth (cm)" optional>
                  <input
                    id="soil-depth"
                    className="input input-narrow"
                    inputMode="numeric"
                    value={soil.samplingDepth}
                    onChange={(event) => patchSoil({ samplingDepth: event.target.value })}
                  />
                </Field>
                <Field id="soil-date" label="Sample date" optional>
                  <input
                    id="soil-date"
                    className="input"
                    type="date"
                    value={soil.sampleDate}
                    onChange={(event) => patchSoil({ sampleDate: event.target.value })}
                  />
                </Field>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="info-block">
        <h3>Water and irrigation</h3>
        <div className="form-grid">
          <fieldset className="field">
            <legend className="field-label">Can you irrigate this farm?</legend>
            <div className="radio-row">
              {[
                { value: 'yes', label: 'Yes' },
                { value: 'no', label: 'No, rain-fed' },
                { value: '', label: 'Not sure' },
              ].map((option) => (
                <label key={option.label} className="radio-option">
                  <input
                    type="radio"
                    name="irrigation-available"
                    value={option.value}
                    checked={water.irrigationAvailable === option.value}
                    onChange={() =>
                      patchWater({
                        irrigationAvailable: option.value as OnboardingDraft['water']['irrigationAvailable'],
                      })
                    }
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>

          <Field id="irrigation-type" label="Irrigation method" optional>
            <select
              id="irrigation-type"
              className="input"
              value={water.irrigationType}
              onChange={(event) => patchWater({ irrigationType: event.target.value })}
            >
              {IRRIGATION_OPTIONS.map((option) => (
                <option key={`${option.value}::${option.label}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="water-reliability" label="Water reliability" optional>
            <select
              id="water-reliability"
              className="input"
              value={water.reliability}
              onChange={(event) => patchWater({ reliability: event.target.value })}
            >
              {RELIABILITY_OPTIONS.map((option) => (
                <option key={`${option.value}::${option.label}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </div>

      <div className="info-block">
        <h3>Current and recent crops</h3>
        <p className="info-hint">Add the seasons you remember, newest first.</p>
        <div className="crop-list">
          {crops.map((entry, index) => (
            <div className="crop-row" key={`crop-${index}`}>
              <input
                className="input"
                aria-label={`Season ${index + 1}`}
                placeholder="Winter 2025/26"
                value={entry.season}
                onChange={(event) => updateCrop(index, { season: event.target.value })}
              />
              <input
                className="input"
                aria-label={`Crop ${index + 1}`}
                placeholder="Wheat"
                value={entry.crop}
                onChange={(event) => updateCrop(index, { crop: event.target.value })}
              />
              <button
                type="button"
                className="button button-ghost button-icon"
                aria-label={`Remove crop ${index + 1}`}
                onClick={() => onChange({ crops: crops.filter((_, i) => i !== index) })}
              >
                ×
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          className="button button-ghost"
          onClick={() => onChange({ crops: [...crops, { season: '', crop: '' }] })}
        >
          + Add another season
        </button>
      </div>

      <div className="info-block">
        <h3>What matters most to you?</h3>
        <p className="info-hint">
          Move the sliders. They are converted to relative weights that add up to 100%.
        </p>
        <div className="priority-list">
          {PRIORITY_FIELDS.map((field) => (
            <label key={field.key} className="priority-row">
              <span className="priority-text">
                <strong>{field.label}</strong>
                <span className="priority-hint">{field.hint}</span>
              </span>
              <span className="priority-control">
                <input
                  type="range"
                  min={0}
                  max={10}
                  step={1}
                  value={priorities[field.key]}
                  aria-label={field.label}
                  onChange={(event) =>
                    onChange({
                      priorities: { ...priorities, [field.key]: Number(event.target.value) },
                    })
                  }
                />
                <span className="priority-value">
                  {Math.round((weights[field.apiKey] ?? 0) * 100)}%
                </span>
              </span>
            </label>
          ))}
        </div>
      </div>

      <div className="info-block">
        <h3>Practical limitations</h3>
        <div className="checkbox-list">
          <label className="checkbox-option">
            <input
              type="checkbox"
              checked={constraints.noMachinery}
              onChange={(event) => patchConstraints({ noMachinery: event.target.checked })}
            />
            We do not have a mechanised harvester
          </label>
          <label className="checkbox-option">
            <input
              type="checkbox"
              checked={constraints.familyLaborOnly}
              onChange={(event) => patchConstraints({ familyLaborOnly: event.target.checked })}
            />
            Work is done by family labour only
          </label>
        </div>
        <Field id="seed-availability" label="Seed availability" optional>
          <select
            id="seed-availability"
            className="input"
            value={constraints.seedAvailability}
            onChange={(event) => patchConstraints({ seedAvailability: event.target.value })}
          >
            {SEED_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {errors.priorities ? <Banner tone="error">{errors.priorities}</Banner> : null}
      {errors.current_crops ? <Banner tone="error">{errors.current_crops}</Banner> : null}
    </section>
  )
}
