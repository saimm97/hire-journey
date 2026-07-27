import { cn } from "@/lib/utils"

const MILESTONES = ["Profile", "Preferences", "Search", "Matches", "Tailor", "Apply", "Track"] as const

export type Milestone = (typeof MILESTONES)[number]

/** The signature progress rail. Completed dots fill emerald; the current one pulses. */
export function JourneySpine({ current = "Profile" }: { current?: Milestone }) {
  const currentIndex = MILESTONES.indexOf(current)
  return (
    <div className="border-b border-brand-border bg-brand-surface px-6 py-4">
      <div className="relative mx-auto flex max-w-5xl items-center justify-between">
        <div className="absolute inset-x-0 top-2 h-0.5 rounded-full bg-brand-border" />
        {MILESTONES.map((label, index) => {
          const done = index < currentIndex
          const active = index === currentIndex
          return (
            <div key={label} className="relative z-10 flex flex-col items-center gap-1.5">
              <span
                className={cn(
                  "size-4 rounded-full ring-4 ring-brand-surface",
                  done && "bg-brand-emerald",
                  active && "animate-pulse bg-gradient-to-r from-brand-coral to-brand-violet",
                  !done && !active && "bg-brand-border",
                )}
              />
              <span
                className={cn(
                  "text-sm font-medium",
                  active ? "font-bold text-brand-ink" : "text-brand-muted",
                  !active && !done && "opacity-60",
                )}
              >
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
