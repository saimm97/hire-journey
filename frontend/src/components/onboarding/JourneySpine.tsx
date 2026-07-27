import { Check } from "lucide-react"

import { cn } from "@/lib/utils"

export const ONBOARDING_STEPS = ["Resume", "Profile", "Preferences"] as const

export type OnboardingStep = (typeof ONBOARDING_STEPS)[number]

interface JourneySpineProps {
  current: OnboardingStep | null
  completed?: OnboardingStep[]
}

/** Progress that reflects saved wizard state; null renders a deliberately neutral rail. */
export function JourneySpine({ current, completed = [] }: JourneySpineProps) {
  const completedSteps = new Set(completed)

  return (
    <nav
      className="border-b border-brand-border bg-white px-4 py-5 sm:px-6"
      aria-label="Onboarding progress"
    >
      <ol className="mx-auto grid max-w-5xl grid-cols-3 gap-2 sm:gap-6">
        {ONBOARDING_STEPS.map((label, index) => {
          const active = current === label
          const done = completedSteps.has(label) && !active
          const state = done ? "completed" : active ? "active" : "upcoming"

          return (
            <li
              key={label}
              data-state={state}
              aria-current={active ? "step" : undefined}
              className="flex min-w-0 flex-col items-center gap-1.5 text-center sm:flex-row sm:gap-3 sm:text-left"
            >
              <span
                className={cn(
                  "flex size-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold",
                  done && "border-brand-emerald bg-brand-emerald text-white",
                  active && "border-brand-primary bg-brand-primary text-white",
                  !done && !active && "border-brand-border bg-brand-surface text-brand-muted",
                )}
                aria-hidden="true"
              >
                {done ? <Check className="size-4" /> : index + 1}
              </span>
              <span
                className={cn(
                  "break-words text-xs font-medium sm:text-sm",
                  done && "text-brand-emerald",
                  active && "font-semibold text-brand-primary",
                  !done && !active && "text-brand-muted",
                )}
              >
                {label}
                {done && <span className="sr-only">, completed</span>}
              </span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}
