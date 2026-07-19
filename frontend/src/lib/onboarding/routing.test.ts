import { describe, expect, it } from 'vitest'

import { makeProfile, makeSnapshot } from '@/test/fixtures'
import { onboardingDestination } from './routing'

describe('onboardingDestination', () => {
  it('sends users with no profile to the profile step', () => {
    expect(onboardingDestination(null)).toBe('/onboarding/profile')
  })

  it('sends users without a source resume to the profile step', () => {
    expect(onboardingDestination(makeSnapshot({ source_resume: null }))).toBe(
      '/onboarding/profile',
    )
  })

  it('sends users with incomplete core details back to the profile step', () => {
    const snapshot = makeSnapshot({ profile: makeProfile({ title: null }) })
    expect(onboardingDestination(snapshot)).toBe('/onboarding/profile')
    const blank = makeSnapshot({ profile: makeProfile({ first_name: '   ' }) })
    expect(onboardingDestination(blank)).toBe('/onboarding/profile')
  })

  it('sends users with details done but preferences missing to preferences', () => {
    expect(onboardingDestination(makeSnapshot())).toBe('/onboarding/preferences')
  })

  it('sends completed users into the app', () => {
    expect(onboardingDestination(makeSnapshot({ onboarding_complete: true }))).toBe('/')
  })
})
