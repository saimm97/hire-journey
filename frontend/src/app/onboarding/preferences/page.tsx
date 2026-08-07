'use client'

import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { OnboardingLoadError } from '@/components/onboarding/OnboardingLoadError'
import { OnboardingShell } from '@/components/onboarding/OnboardingShell'
import { PreferencesForm } from '@/components/onboarding/PreferencesForm'
import { Toast } from '@/components/onboarding/Toast'
import { WizardFooter } from '@/components/onboarding/WizardFooter'
import { usePreferences } from '@/hooks/usePreferences'
import { COMPLETED_DESTINATION } from '@/lib/onboarding/routing'

export default function OnboardingPreferences() {
  const router = useRouter()
  const state = usePreferences()

  useEffect(() => {
    if (state.redirectTo) router.replace(state.redirectTo)
  }, [state.redirectTo, router])

  const ready = state.status === 'ready'

  return (
    <OnboardingShell
      step={ready ? 'Preferences' : null}
      completedSteps={ready ? ['Resume', 'Profile'] : []}
      title="What are you looking for?"
      subtitle="Tell us your target roles and terms — this drives your job matches."
    >
      {state.status === 'loading' && (
        <div className="flex items-center justify-center gap-2 py-24 text-brand-muted">
          <Loader2 className="size-5 animate-spin" /> Loading…
        </div>
      )}
      {state.status === 'load_error' && (
        <OnboardingLoadError message={state.loadError} onRetry={state.retry} />
      )}
      {ready && <PreferencesForm state={state} />}
      {ready && (
        <WizardFooter
          label="Finish setup"
          note="You can change these anytime."
          saving={state.saving}
          onBack={() => router.push('/onboarding/profile')}
          onSave={async () => {
            if (await state.save()) router.push(COMPLETED_DESTINATION)
          }}
        />
      )}
      <Toast toast={state.toast} onDismiss={state.dismissToast} />
    </OnboardingShell>
  )
}
