"use client"

import { MapPin } from "lucide-react"

import type { PreferencesState } from "@/hooks/usePreferences"
import type { SeniorityLevel, WorkMode } from "@/lib/api/types"
import { WORK_MODES } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { ChipInput } from "./ChipInput"
import { MultiSelect } from "./MultiSelect"
import { PillSelect, type PillOption } from "./PillSelect"
import { SalaryField } from "./SalaryField"
import { Section } from "./Section"

const ROLE_SUGGESTIONS = [
  "Backend Engineer",
  "Frontend Engineer",
  "Full-Stack Engineer",
  "ML Engineer",
  "Data Engineer",
  "DevOps Engineer",
  "Platform Engineer",
]

const WORK_MODE_LABELS: Record<WorkMode, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
}

const SENIORITY_OPTIONS: PillOption<SeniorityLevel>[] = [
  { value: "intern", label: "Intern" },
  { value: "entry_level", label: "Entry level" },
  { value: "associate", label: "Associate" },
  { value: "mid_level", label: "Mid level" },
  { value: "senior", label: "Senior" },
  { value: "lead", label: "Lead" },
  { value: "manager", label: "Manager" },
  { value: "director", label: "Director" },
]

/** The preferences step: roles, locations, work modes, seniority, salary. */
export function PreferencesForm({ state }: { state: PreferencesState }) {
  return (
    <div className="space-y-10 rounded-2xl border border-brand-border bg-white p-6 shadow-[0_4px_20px_rgba(35,31,28,0.04)] sm:p-8">
      <Section title="Desired roles">
        <MultiSelect
          values={state.roles}
          onAdd={state.addRole}
          onRemove={state.removeRole}
          options={ROLE_SUGGESTIONS}
          allowCustom
          placeholder="Add a role…"
          addLabel="Add role"
        />
      </Section>

      <Section title="Desired locations">
        <ChipInput
          values={state.locations}
          onAdd={state.addLocation}
          onRemove={state.removeLocation}
          placeholder="City, country, or region…"
          icon={MapPin}
          addLabel="Add location"
        />
      </Section>

      <Section title="Work modes">
        <div className="flex flex-wrap gap-2">
          {WORK_MODES.map((mode) => {
            const active = state.workModes.includes(mode)
            return (
              <button
                key={mode}
                type="button"
                aria-pressed={active}
                onClick={() => state.toggleWorkMode(mode)}
                className={cn(
                  "rounded-full border px-4 py-1.5 text-sm transition-colors",
                  active
                    ? "border-brand-violet bg-brand-violet/10 font-medium text-brand-ink"
                    : "border-brand-border bg-white text-brand-muted hover:border-brand-violet/60 hover:text-brand-ink",
                )}
              >
                {WORK_MODE_LABELS[mode]}
              </button>
            )
          })}
        </div>
      </Section>

      <Section title="Seniority">
        <PillSelect
          options={SENIORITY_OPTIONS}
          value={state.seniority}
          onChange={state.setSeniority}
        />
      </Section>

      <Section title="Minimum salary">
        <SalaryField value={state.minimumSalary} onChange={state.setMinimumSalary} />
      </Section>
    </div>
  )
}
