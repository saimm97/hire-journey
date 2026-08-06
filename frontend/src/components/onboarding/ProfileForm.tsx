"use client"

import { FileCheck2, Loader2, RefreshCw } from "lucide-react"

import type { ProfileDraftState } from "@/hooks/useProfileDraft"
import { Button } from "@/components/ui/button"
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

/**
 * What this form needs: the editable draft, plus the resume and project-conflict
 * affordances that sit around it. Deliberately narrower than the details hook —
 * nothing here should reach for loading, saving, or routing state.
 */
export interface ProfileFormState
  extends Pick<
    ProfileDraftState,
    | "identity"
    | "setIdentityField"
    | "socialLinks"
    | "setSocialLink"
    | "summary"
    | "setSummary"
    | "technologies"
    | "addTechnology"
    | "removeTechnology"
    | "education"
    | "certifications"
    | "employment"
    | "projects"
    | "fieldError"
  > {
  accountEmail: string
  reupload: () => void
  projectConflict: string | null
  reloadingProjects: boolean
  reloadProjects: () => Promise<boolean>
}

/** The complete, editable details step — every extracted section in one form. */
export function ProfileForm({ state }: { state: ProfileFormState }) {
  return (
    <div className="divide-y divide-brand-border rounded-xl border border-brand-border bg-white px-6 sm:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3 py-6">
        <div className="flex items-center gap-2">
          <FileCheck2 className="size-5 text-brand-emerald" />
          <span className="font-medium text-brand-ink">Resume parsed</span>
          <AutoFilledBadge label="Everything below is editable" />
        </div>
        <Button
          type="button"
          onClick={state.reupload}
          variant="outline"
          size="sm"
        >
          <RefreshCw className="size-3.5" /> Upload a different resume
        </Button>
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
            <Button
              type="button"
              onClick={() => void state.reloadProjects()}
              disabled={state.reloadingProjects}
              variant="outline"
              size="sm"
              className="border-red-300 text-red-700 hover:border-red-500 hover:bg-red-50 hover:text-red-700 disabled:cursor-wait"
            >
              {state.reloadingProjects ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <RefreshCw className="size-3.5" />
              )}
              {state.reloadingProjects ? "Reloading projects…" : "Reload latest projects"}
            </Button>
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
