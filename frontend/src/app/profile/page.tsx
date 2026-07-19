'use client'

import { useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { PreferencesForm } from '@/components/onboarding/PreferencesForm'
import { ProfileForm } from '@/components/onboarding/ProfileForm'
import { ResumeDropzone } from '@/components/onboarding/ResumeDropzone'
import { Toast } from '@/components/onboarding/Toast'
import { AppShell } from '@/components/layout/AppShell'
import { useOnboardingProfile } from '@/hooks/useOnboardingProfile'
import { usePreferences } from '@/hooks/usePreferences'

const SAVE_BUTTON =
  'inline-flex items-center gap-2 rounded-full bg-brand-coral px-6 py-2.5 font-semibold ' +
  'text-white shadow-sm transition-colors hover:bg-brand-coral-dark disabled:opacity-60'

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
    <AppShell active="profile">
      <div className="mb-8 space-y-1">
        <h1 className="font-display text-3xl font-semibold text-brand-ink">Your profile</h1>
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
        {(details.status === 'empty' || details.status === 'parsing') && (
          <ResumeDropzone onFile={details.uploadCv} parsing={details.status === 'parsing'} />
        )}
        {details.status === 'ready' && (
          <section className="space-y-4">
            <ProfileForm state={details} />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={details.saveAndContinue}
                disabled={details.saving}
                className={SAVE_BUTTON}
              >
                {details.saving && <Loader2 className="size-4 animate-spin" />}
                Save details
              </button>
            </div>
          </section>
        )}

        {preferences.status === 'ready' && (
          <section className="space-y-4">
            <h2 className="font-mono text-[11px] uppercase tracking-wider text-brand-muted">
              Job preferences
            </h2>
            <PreferencesForm state={preferences} />
            <div className="flex justify-end">
              <button
                type="button"
                onClick={preferences.save}
                disabled={preferences.saving}
                className={SAVE_BUTTON}
              >
                {preferences.saving && <Loader2 className="size-4 animate-spin" />}
                Save preferences
              </button>
            </div>
          </section>
        )}
      </div>

      <Toast toast={details.toast} onDismiss={details.dismissToast} />
      <Toast toast={preferences.toast} onDismiss={preferences.dismissToast} />
    </AppShell>
  )
}
