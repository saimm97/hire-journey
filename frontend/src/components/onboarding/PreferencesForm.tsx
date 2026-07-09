"use client"

import { MapPin, Search } from "lucide-react"

import type { usePreferences, WorkMode } from "@/hooks/usePreferences"
import { ChipInput } from "./ChipInput"
import { MultiSelect } from "./MultiSelect"
import { SalaryField } from "./SalaryField"
import { SegmentedControl, type SegmentOption } from "./SegmentedControl"
import { Section } from "./Section"
import { Toggle } from "./Toggle"

type PreferencesState = ReturnType<typeof usePreferences>

const ROLE_SUGGESTIONS = [
  "Machine Learning Engineer",
  "AI Engineer",
  "Backend Engineer",
  "Full-Stack Engineer",
  "Data Scientist",
  "MLOps Engineer",
  "Platform Engineer",
  "Software Engineer",
]

const SENIORITY_LEVELS = [
  "Intern",
  "Entry level",
  "Associate",
  "Mid level",
  "Senior",
  "Lead",
  "Manager",
  "Director",
]

const WORK_MODES: SegmentOption<WorkMode>[] = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "Onsite" },
]

/** The targeting card: roles and salary persist; locations and work mode are local for now. */
export function PreferencesForm({ state }: { state: PreferencesState }) {
  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-brand-border bg-white p-6 shadow-[0_4px_20px_rgba(35,31,28,0.04)]">
      <Section title="Target roles">
        <MultiSelect
          values={state.roles}
          onAdd={state.addRole}
          onRemove={state.removeRole}
          options={ROLE_SUGGESTIONS}
          allowCustom
          icon={Search}
          placeholder="e.g. Machine Learning Engineer, Backend Engineer…"
          addLabel="Add role"
        />
      </Section>

      <Section title="Seniority level">
        <MultiSelect
          values={state.seniority}
          onAdd={state.addSeniority}
          onRemove={state.removeSeniority}
          options={SENIORITY_LEVELS}
          addLabel="Add seniority level"
        />
      </Section>

      <Section
        title="Locations"
        action={
          <Toggle
            label="Open to relocating"
            checked={state.openToRelocating}
            onChange={state.setOpenToRelocating}
          />
        }
      >
        <ChipInput
          values={state.locations}
          onAdd={state.addLocation}
          onRemove={state.removeLocation}
          icon={MapPin}
          placeholder="Search cities or regions…"
          addLabel="Add location"
        />
      </Section>

      <Section title="Work mode">
        <SegmentedControl options={WORK_MODES} value={state.workMode} onChange={state.setWorkMode} />
      </Section>

      <Section title="Salary expectations">
        <SalaryField value={state.minimumSalary} onChange={state.setMinimumSalary} />
      </Section>
    </div>
  )
}
