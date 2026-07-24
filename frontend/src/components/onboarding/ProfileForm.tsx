"use client"

import { FileCheck2, Loader2, RefreshCw } from "lucide-react"

import type { OnboardingProfileState } from "@/hooks/useOnboardingProfile"
import { AutoFilledBadge } from "./AutoFilledBadge"
import { CertificationEditor } from "./CertificationEditor"
import { ChipInput } from "./ChipInput"
import { EducationEditor } from "./EducationEditor"
import { EmploymentEditor } from "./EmploymentEditor"
import { IdentityFields } from "./IdentityFields"
import { LinksFields } from "./LinksFields"
import { ProjectsEditor } from "./ProjectsEditor"
import { ResumeSummary } from "./ResumeSummary"
import { Section } from "./Section"

/** The complete, editable details step — every extracted section in one form. */
export function ProfileForm({ state }: { state: OnboardingProfileState }) {
  return (
    <div className="space-y-10 rounded-2xl border border-brand-border bg-white p-6 shadow-[0_4px_20px_rgba(35,31,28,0.04)] sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-brand-border pb-4">
        <div className="flex items-center gap-2">
          <FileCheck2 className="size-5 text-brand-emerald" />
          <span className="font-medium text-brand-ink">Resume parsed</span>
          <AutoFilledBadge label="Everything below is editable" />
        </div>
        <button
          type="button"
          onClick={state.reupload}
          className="inline-flex items-center gap-1.5 rounded-full border border-brand-border px-3 py-1.5 text-sm text-brand-muted transition-colors hover:border-brand-violet/60 hover:text-brand-ink"
        >
          <RefreshCw className="size-3.5" /> Upload a different resume
        </button>
      </div>

      <Section title="Your details">
        <IdentityFields
          identity={state.identity}
          accountEmail={state.accountEmail}
          onChange={state.setIdentityField}
          fieldError={state.fieldError}
        />
      </Section>

      <Section title="Links">
        <LinksFields
          links={state.socialLinks}
          onChange={state.setSocialLink}
          fieldError={state.fieldError}
        />
      </Section>

      <ResumeSummary summary={state.summary} onChange={state.setSummary} />

      <Section title="Technologies">
        <ChipInput
          values={state.technologies}
          onAdd={state.addTechnology}
          onRemove={state.removeTechnology}
          placeholder="Add a technology…"
          addLabel="Add technology"
          fieldPath="technologies"
          error={state.fieldError("technologies")}
        />
      </Section>

      <Section
        title="Employment history"
        fieldPath="employment_history"
        error={state.fieldError("employment_history")}
      >
        <EmploymentEditor controller={state.employment} />
      </Section>

      <Section
        title="Education"
        fieldPath="education"
        error={state.fieldError("education")}
      >
        <EducationEditor controller={state.education} />
      </Section>

      <Section
        title="Certifications"
        fieldPath="certifications"
        error={state.fieldError("certifications")}
      >
        <CertificationEditor controller={state.certifications} />
      </Section>

      <Section
        title="Projects"
        fieldPath="projects"
        error={state.projectConflict ?? state.fieldError("projects")}
        action={
          state.projectConflict ? (
            <button
              type="button"
              onClick={() => void state.reloadProjects()}
              disabled={state.reloadingProjects}
              className="inline-flex items-center gap-1.5 rounded-full border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 transition-colors hover:border-red-500 disabled:cursor-wait disabled:opacity-60"
            >
              {state.reloadingProjects ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <RefreshCw className="size-3.5" />
              )}
              {state.reloadingProjects ? "Reloading projects…" : "Reload latest projects"}
            </button>
          ) : undefined
        }
      >
        <fieldset
          disabled={state.reloadingProjects}
          aria-busy={state.reloadingProjects}
          className="min-w-0 border-0 p-0 disabled:opacity-60"
        >
          <ProjectsEditor controller={state.projects} />
        </fieldset>
      </Section>
    </div>
  )
}
