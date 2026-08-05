'use client'

import { useEffect, useState } from 'react'
import { Loader2, Pencil } from 'lucide-react'
import { useRouter } from 'next/navigation'

import { AppShell } from '@/components/layout/AppShell'
import { OnboardingLoadError } from '@/components/onboarding/OnboardingLoadError'
import { PreferencesForm } from '@/components/onboarding/PreferencesForm'
import { ProfileForm } from '@/components/onboarding/ProfileForm'
import { ResumeDropzone } from '@/components/onboarding/ResumeDropzone'
import { Toast } from '@/components/onboarding/Toast'
import { ProfileOverview } from '@/components/profile/ProfileOverview'
import { Button } from '@/components/ui/button'
import { useOnboardingProfile } from '@/hooks/useOnboardingProfile'
import { usePreferences } from '@/hooks/usePreferences'

/** Post-onboarding profile: read-first, with the hardened forms available on demand. */
export default function ProfilePage() {
  const router = useRouter()
  const [editing, setEditing] = useState(false)
  const details = useOnboardingProfile({
    guardCompleted: false,
  })
  const preferences = usePreferences({
    guardCompleted: false,
    successMessage: 'Profile saved.',
  })

  // Un-onboarded visitors get sent back into the wizard.
  useEffect(() => {
    if (preferences.redirectTo) router.replace(preferences.redirectTo)
  }, [preferences.redirectTo, router])

  const ready = details.status === 'ready' && preferences.status === 'ready'
  const loading = details.status === 'loading' || preferences.status === 'loading'
  const loadError = details.loadError ?? preferences.loadError

  const retryAll = () => {
    details.retry()
    preferences.retry()
  }

  const cancelEditing = () => {
    setEditing(false)
    details.dismissToast()
    preferences.dismissToast()
    retryAll()
  }

  const saveProfile = async () => {
    if (!(await details.saveAndContinue())) return
    if (!(await preferences.save())) return
    setEditing(false)
  }
  

  return (
    <AppShell>
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-[32px] font-semibold leading-10 tracking-tight text-brand-ink">
            Your profile
          </h1>
          <p className="text-brand-muted">
            Everything below feeds your job matching — keep it current.
          </p>
        </div>
        {ready && !editing && (
          <Button type="button" onClick={() => setEditing(true)} size="lg">
            <Pencil className="size-4" /> Edit profile
          </Button>
        )}
      </div>

      <div>
        {loading && (
          <div className="flex items-center justify-center gap-2 py-24 text-brand-muted">
            <Loader2 className="size-5 animate-spin" /> Loading…
          </div>
        )}
        {!loading && loadError && (
          <OnboardingLoadError message={loadError} onRetry={retryAll} />
        )}
        {!loading && !loadError && (details.status === 'empty' || details.status === 'parsing') && (
          <ResumeDropzone onFile={details.uploadCv} parsing={details.status === 'parsing'} />
        )}

        {ready && !editing && (
          <ProfileOverview
            details={{
              identity: details.identity,
              accountEmail: details.accountEmail,
              socialLinks: details.socialLinks,
              summary: details.summary,
              technologies: details.technologies,
              employment: details.employment.items,
              education: details.education.items,
              certifications: details.certifications.items,
              projects: details.projects.items,
            }}
            preferences={{
              roles: preferences.roles,
              locations: preferences.locations,
              workModes: preferences.workModes,
              seniority: preferences.seniority,
              minimumSalary: preferences.minimumSalary,
            }}
          />
        )}

        {ready && editing && (
          <div className="space-y-10">
            <ProfileForm state={details} />
            <section className="space-y-4" aria-labelledby="edit-job-preferences">
              <h2 id="edit-job-preferences" className="text-xl font-semibold text-brand-ink">
                Job preferences
              </h2>
              <PreferencesForm state={preferences} />
            </section>
            <div className="flex flex-col-reverse gap-3 border-t border-brand-border pt-6 sm:flex-row sm:justify-end">
              <Button type="button" onClick={cancelEditing} variant="outline" size="lg">
                Cancel
              </Button>
              <Button
                type="button"
                onClick={() => void saveProfile()}
                disabled={details.saving || preferences.saving}
                size="lg"
              >
                {(details.saving || preferences.saving) && (
                  <Loader2 className="size-4 animate-spin" />
                )}
                Save profile
              </Button>
            </div>
          </div>
        )}
      </div>

      <Toast toast={details.toast} onDismiss={details.dismissToast} />
      <Toast toast={preferences.toast} onDismiss={preferences.dismissToast} />
    </AppShell>
  )
}
