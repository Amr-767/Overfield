// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { Stepper } from './Stepper'

const STEPS = [
  { id: 'profile', label: 'Profile' },
  { id: 'details', label: 'Farm' },
  { id: 'boundary', label: 'Boundary' },
  { id: 'info', label: 'Details' },
  { id: 'review', label: 'Review' },
]

afterEach(cleanup)

describe('Stepper', () => {
  it('marks the current step and shows completed steps with a check', () => {
    render(<Stepper steps={STEPS} current={1} maxReached={1} />)

    const current = screen.getByRole('button', { name: /Farm/ })
    expect(current.getAttribute('aria-current')).toBe('step')

    const completed = screen.getByRole('button', { name: 'Profile' })
    expect(completed.querySelector('.stepper-index')?.textContent).toBe('✓')
  })

  it('disables steps the farmer has not reached yet', () => {
    render(<Stepper steps={STEPS} current={0} maxReached={0} />)
    const review = screen.getByRole('button', { name: /Review/ })
    expect((review as HTMLButtonElement).disabled).toBe(true)
  })

  it('lets the farmer go back to a completed step', async () => {
    const onSelect = vi.fn()
    render(<Stepper steps={STEPS} current={2} maxReached={2} onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Farm' }))
    expect(onSelect).toHaveBeenCalledWith(1)
  })

  it('does not fire a selection for the current step', async () => {
    const onSelect = vi.fn()
    render(<Stepper steps={STEPS} current={2} maxReached={2} onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: /Boundary/ }))
    expect(onSelect).not.toHaveBeenCalled()
  })
})
