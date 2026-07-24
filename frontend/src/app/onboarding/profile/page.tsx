'use client'

import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { OnboardingLoadError } from '@/components/onboarding/OnboardingLoadError'
import { OnboardingShell } from '@/components/onboarding/OnboardingShell'
import { ProfileForm } from '@/components/onboarding/ProfileForm'
import { ResumeDropzone } from '@/components/onboarding/ResumeDropzone'
import { Toast } from '@/components/onboarding/Toast'
import { WizardFooter } from '@/components/onboarding/WizardFooter'
import { useOnboardingProfile } from '@/hooks/useOnboardingProfile'

export default function OnboardingProfile() {
  const router = useRouter()
  const state = useOnboardingProfile()

  useEffect(() => {
    if (state.redirectTo) router.replace(state.redirectTo)
  }, [state.redirectTo, router])

  return (
    <OnboardingShell
      step="Profile"
      title="Build your profile"
      subtitle="Upload your resume — we'll read it and fill everything in. You can fix anything."
    >
      {state.status === 'loading' && (
        <div className="flex items-center justify-center gap-2 py-24 text-brand-muted">
          <Loader2 className="size-5 animate-spin" /> Loading…
        </div>
      )}
      {state.status === 'load_error' && (
        <OnboardingLoadError message={state.loadError} onRetry={state.retry} />
      )}
      {(state.status === 'empty' || state.status === 'parsing') && (
        <ResumeDropzone onFile={state.uploadCv} parsing={state.status === 'parsing'} />
      )}
      {state.status === 'ready' && <ProfileForm state={state} />}
      {state.status === 'ready' && (
        <WizardFooter
          note="Preferences are up next — you can edit all of this later."
          saving={state.saving}
          onSave={async () => {
            if (await state.saveAndContinue()) router.push('/onboarding/preferences')
          }}
        />
      )}
      <Toast toast={state.toast} onDismiss={state.dismissToast} />
    </OnboardingShell>
  )
}
