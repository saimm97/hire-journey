"use client"

import { useRouter } from "next/navigation"

import { JourneySpine } from "@/components/onboarding/JourneySpine"
import { ProfileForm } from "@/components/onboarding/ProfileForm"
import { ResumeDropzone } from "@/components/onboarding/ResumeDropzone"
import { Toast } from "@/components/onboarding/Toast"
import { WizardFooter } from "@/components/onboarding/WizardFooter"
import { useProfileOnboarding } from "@/hooks/useProfileOnboarding"

const NEXT_ROUTE = "/onboarding/preferences"

export default function ProfileOnboardingPage() {
  const state = useProfileOnboarding()
  const router = useRouter()
  const showForm = state.status === "ready"

  const saveAndContinue = async () => {
    if (await state.saveAndContinue()) router.push(NEXT_ROUTE)
  }

  return (
    <div className="flex min-h-screen flex-col bg-brand-paper">
      <header className="sticky top-0 z-30 flex items-center justify-between bg-brand-paper px-6 py-4">
        <span className="font-display text-xl font-bold text-brand-violet">Hire Journey</span>
        <span className="text-sm text-brand-muted">Onboarding</span>
      </header>

      <JourneySpine current="Profile" />

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12 pb-32">
        <div className="mx-auto max-w-2xl space-y-3 text-center">
          <h1 className="font-display text-4xl font-extrabold tracking-tight text-brand-ink">
            Let&apos;s build your profile
          </h1>
          <p className="text-lg text-brand-muted">
            Upload your resume and we&apos;ll pull out your details. Review and adjust anything
            before moving on.
          </p>
        </div>

        {state.status === "loading" ? (
          <div className="flex justify-center py-16 text-brand-muted">Loading…</div>
        ) : showForm ? (
          <ProfileForm state={state} />
        ) : (
          <ResumeDropzone onFile={state.uploadCv} parsing={state.status === "parsing"} />
        )}
      </main>

      {showForm && (
        <WizardFooter
          note="Your edits save to your profile."
          saving={state.saving}
          onSave={saveAndContinue}
        />
      )}

      <Toast toast={state.toast} onDismiss={state.dismissToast} />
    </div>
  )
}
