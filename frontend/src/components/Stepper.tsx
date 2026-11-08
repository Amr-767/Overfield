interface Step {
  id: string
  label: string
}

interface StepperProps {
  steps: Step[]
  current: number
  maxReached: number
  onSelect?: (index: number) => void
}

export function Stepper({ steps, current, maxReached, onSelect }: StepperProps) {
  return (
    <ol className="stepper" aria-label="Onboarding progress">
      {steps.map((step, index) => {
        const state =
          index === current ? 'current' : index < current ? 'complete' : 'upcoming'
        const reachable = index <= maxReached && index !== current
        return (
          <li key={step.id} className={`stepper-item stepper-${state}`}>
            <button
              type="button"
              className="stepper-button"
              disabled={!reachable}
              aria-current={index === current ? 'step' : undefined}
              onClick={() => reachable && onSelect?.(index)}
            >
              <span className="stepper-index" aria-hidden="true">
                {index < current ? '✓' : index + 1}
              </span>
              <span className="stepper-label">{step.label}</span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}
