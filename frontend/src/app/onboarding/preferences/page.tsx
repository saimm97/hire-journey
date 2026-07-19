'use client'

import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { OnboardingShell } from '@/components/onboarding/OnboardingShell'
import { PreferencesForm } from '@/components/onboarding/PreferencesForm'
import { Toast } from '@/components/onboarding/Toast'
import { WizardFooter } from '@/components/onboarding/WizardFooter'
import { usePreferences } from '@/hooks/usePreferences'

export default function OnboardingPreferences() {
  const router = useRouter()
  const state = usePreferences()

  useEffect(() => {
    if (state.redirectTo) router.replace(state.redirectTo)
  }, [state.redirectTo, router])

  return (
    <OnboardingShell
      step="Preferences"
      title="What are you looking for?"
      subtitle="Tell us your target roles and terms — this drives your job matches."
    >
      {state.status === 'loading' ? (
        <div className="flex items-center justify-center gap-2 py-24 text-brand-muted">
          <Loader2 className="size-5 animate-spin" /> Loading…
        </div>
      ) : (
        <PreferencesForm state={state} />
      )}
      {state.status === 'ready' && (
        <WizardFooter
          label="Finish setup"
          note="You can change these anytime."
          saving={state.saving}
          onBack={() => router.push('/onboarding/profile')}
          onSave={async () => {
            if (await state.save()) router.push('/')
          }}
        />
      )}
      <Toast toast={state.toast} onDismiss={state.dismissToast} />
    </OnboardingShell>
  )
}
