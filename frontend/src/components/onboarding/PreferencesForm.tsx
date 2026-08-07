"use client"

import type { PreferencesState } from "@/hooks/usePreferences"
import type { SeniorityLevel, WorkMode } from "@/lib/api/types"
import { WORK_MODES } from "@/lib/api/types"
import { cn } from "@/lib/utils"
import { Chip } from "./Chip"
import { LazyLocationPicker } from "./LazyLocationPicker"
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

// Fields that own a dedicated Section below; anything else surfaces in the summary.
const SECTION_FIELDS = [
  "desired_roles",
  "desired_locations",
  "work_modes_preferred",
  "seniority_level",
  "minimum_salary",
]

/** The preferences step: roles, locations, work modes, seniority, salary. */
export function PreferencesForm({ state }: { state: PreferencesState }) {
  // Any field error not addressable by a Section — should be rare, but never
  // leave one invisible (it would read as "fix the field" with nothing lit up).
  const unmapped = Object.entries(state.fieldErrors).filter(
    ([key]) => !SECTION_FIELDS.some((field) => key === field || key.startsWith(`${field}.`)),
  )

  return (
    <div className="divide-y divide-brand-border rounded-xl border border-brand-border bg-white px-6 sm:px-8">
      {unmapped.length > 0 && (
        <div className="my-6 rounded-lg border border-red-500 bg-red-50 p-4 text-sm text-red-700">
          <p className="font-medium">Please fix the following:</p>
          <ul className="mt-1 list-inside list-disc">
            {unmapped.map(([key, message]) => (
              <li key={key}>{message}</li>
            ))}
          </ul>
        </div>
      )}

      <Section
        title="Desired roles"
        fieldPath="desired_roles"
        error={state.groupError("desired_roles")}
      >
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

      <Section
        title="Desired locations"
        fieldPath="desired_locations"
        error={state.groupError("desired_locations")}
      >
        <div className="space-y-3">
          <LazyLocationPicker buttonLabel="Add location" onSelect={state.addLocation} />
          {state.locations.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {state.locations.map((value) => (
                <Chip
                  key={value}
                  value={value}
                  onRemove={() => state.removeLocation(value)}
                />
              ))}
            </div>
          )}
        </div>
      </Section>

      <Section
        title="Work modes"
        fieldPath="work_modes_preferred"
        error={state.groupError("work_modes_preferred")}
      >
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
                    ? "border-brand-primary bg-brand-primary/10 font-medium text-brand-ink"
                    : "border-brand-border bg-white text-brand-muted hover:border-brand-primary/60 hover:text-brand-ink",
                )}
              >
                {WORK_MODE_LABELS[mode]}
              </button>
            )
          })}
        </div>
      </Section>

      <Section
        title="Seniority"
        fieldPath="seniority_level"
        error={state.fieldError("seniority_level")}
      >
        <PillSelect
          options={SENIORITY_OPTIONS}
          value={state.seniority}
          onChange={state.setSeniority}
        />
      </Section>

      <Section
        title="Minimum salary"
        fieldPath="minimum_salary"
        error={state.fieldError("minimum_salary")}
      >
        <SalaryField value={state.minimumSalary} onChange={state.setMinimumSalary} />
      </Section>
    </div>
  )
}
