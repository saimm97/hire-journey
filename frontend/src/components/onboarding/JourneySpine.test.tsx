import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { JourneySpine } from './JourneySpine'

const step = (name: string) => screen.getByText(name).closest('li')

describe('JourneySpine', () => {
  it('renders neutral progress while onboarding state is unresolved', () => {
    render(<JourneySpine current={null} />)

    expect(screen.queryByRole('listitem', { current: 'step' })).not.toBeInTheDocument()
    for (const name of ['Resume', 'Profile', 'Preferences']) {
      expect(step(name)).toHaveAttribute('data-state', 'upcoming')
    }
  })

  it('marks Resume as the active upload stage', () => {
    render(<JourneySpine current="Resume" />)

    expect(step('Resume')).toHaveAttribute('aria-current', 'step')
    expect(step('Resume')).toHaveAttribute('data-state', 'active')
  })

  it('marks Resume complete when Profile is active', () => {
    render(<JourneySpine current="Profile" completed={['Resume']} />)

    expect(step('Profile')).toHaveAttribute('aria-current', 'step')
    expect(step('Resume')).toHaveAttribute('data-state', 'completed')
    expect(within(step('Resume')!).getByText(/completed/i)).toHaveClass('sr-only')
  })

  it('marks both prior stages complete when Preferences is active', () => {
    render(
      <JourneySpine current="Preferences" completed={['Resume', 'Profile']} />,
    )

    expect(step('Preferences')).toHaveAttribute('aria-current', 'step')
    expect(step('Resume')).toHaveAttribute('data-state', 'completed')
    expect(step('Profile')).toHaveAttribute('data-state', 'completed')
  })
})
