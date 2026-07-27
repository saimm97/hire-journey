'use client'

import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { OnboardingLoadError } from '@/components/onboarding/OnboardingLoadError'
import { PreferencesForm } from '@/components/onboarding/PreferencesForm'
import { ProfileForm } from '@/components/onboarding/ProfileForm'
import { ResumeDropzone } from '@/components/onboarding/ResumeDropzone'
import { Toast } from '@/components/onboarding/Toast'
import { Button } from '@/components/ui/button'
import { useOnboardingProfile } from '@/hooks/useOnboardingProfile'
import { usePreferences } from '@/hooks/usePreferences'

/** Post-onboarding profile editor: the full details + preferences, always editable. */
export default function ProfilePage() {
  const router = useRouter()
  const details = useOnboardingProfile({
    guardCompleted: false,
    successMessage: 'Profile saved.',
  })
  const preferences = usePreferences({
    guardCompleted: false,
    successMessage: 'Preferences saved.',
  })

  // Un-onboarded visitors get sent back into the wizard.
  useEffect(() => {
    if (preferences.redirectTo) router.replace(preferences.redirectTo)
  }, [preferences.redirectTo, router])

  return (
    <AppShell>
      <div className="mb-8 space-y-1">
        <h1 className="text-[32px] font-semibold leading-10 tracking-tight text-brand-ink">
          Your profile
        </h1>
        <p className="text-brand-muted">
          Everything below feeds your job matching — keep it current.
        </p>
      </div>

      <div className="space-y-12">
        {details.status === 'loading' && (
          <div className="flex items-center justify-center gap-2 py-24 text-brand-muted">
            <Loader2 className="size-5 animate-spin" /> Loading…
          </div>
        )}
        {details.status === 'load_error' && (
          <OnboardingLoadError message={details.loadError} onRetry={details.retry} />
        )}
        {(details.status === 'empty' || details.status === 'parsing') && (
          <ResumeDropzone onFile={details.uploadCv} parsing={details.status === 'parsing'} />
        )}
        {details.status === 'ready' && (
          <section className="space-y-4">
            <ProfileForm state={details} />
            <div className="flex justify-end">
              <Button
                type="button"
                onClick={details.saveAndContinue}
                disabled={details.saving}
                size="lg"
              >
                {details.saving && <Loader2 className="size-4 animate-spin" />}
                Save details
              </Button>
            </div>
          </section>
        )}

        {preferences.status === 'load_error' && (
          <OnboardingLoadError message={preferences.loadError} onRetry={preferences.retry} />
        )}
        {preferences.status === 'ready' && (
          <section className="space-y-4">
            <h2 className="text-xl font-semibold text-brand-ink">Job preferences</h2>
            <PreferencesForm state={preferences} />
            <div className="flex justify-end">
              <Button
                type="button"
                onClick={preferences.save}
                disabled={preferences.saving}
                size="lg"
              >
                {preferences.saving && <Loader2 className="size-4 animate-spin" />}
                Save preferences
              </Button>
            </div>
          </section>
        )}
      </div>

      <Toast toast={details.toast} onDismiss={details.dismissToast} />
      <Toast toast={preferences.toast} onDismiss={preferences.dismissToast} />
    </AppShell>
  )
}
