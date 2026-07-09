"use client"

import { useRouter } from "next/navigation"

import { JourneySpine } from "@/components/onboarding/JourneySpine"
import { PreferencesForm } from "@/components/onboarding/PreferencesForm"
import { Toast } from "@/components/onboarding/Toast"
import { WizardFooter } from "@/components/onboarding/WizardFooter"
import { usePreferences } from "@/hooks/usePreferences"

const NEXT_ROUTE = "/"
const BACK_ROUTE = "/onboarding/profile"

export default function PreferencesOnboardingPage() {
  const state = usePreferences()
  const router = useRouter()

  const finish = async () => {
    if (await state.save()) router.push(NEXT_ROUTE)
  }

  return (
    <div className="flex min-h-screen flex-col bg-brand-paper">
      <header className="sticky top-0 z-30 flex items-center justify-between bg-brand-paper px-6 py-4">
        <span className="font-display text-xl font-bold text-brand-violet">Hire Journey</span>
        <span className="text-sm text-brand-muted">Onboarding</span>
      </header>

      <JourneySpine current="Preferences" />

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12 pb-32">
        <div className="mx-auto max-w-2xl space-y-3 text-center">
          <h1 className="font-display text-4xl font-extrabold tracking-tight text-brand-ink">
            Tell us what you&apos;re aiming for
          </h1>
          <p className="text-lg text-brand-muted">
            Define your ideal next role. We&apos;ll use this to calibrate your matches and surface
            the right opportunities.
          </p>
        </div>

        {state.status === "loading" ? (
          <div className="flex justify-center py-16 text-brand-muted">Loading…</div>
        ) : (
          <PreferencesForm state={state} />
        )}
      </main>

      {state.status === "ready" && (
        <WizardFooter
          label="Finish setup"
          note="Target roles and salary save to your profile."
          saving={state.saving}
          onSave={finish}
          onBack={() => router.push(BACK_ROUTE)}
        />
      )}

      <Toast toast={state.toast} onDismiss={state.dismissToast} />
    </div>
  )
}
