"use client"

import { useState } from "react"
import { Check, RefreshCw } from "lucide-react"

import type { useProfileOnboarding } from "@/hooks/useProfileOnboarding"
import type { Project } from "@/lib/api/types"
import { IdentityFields } from "./IdentityFields"
import { LinksFields } from "./LinksFields"
import { ProjectDialog } from "./ProjectDialog"
import { ProjectList } from "./ProjectList"
import { ResumeSummary } from "./ResumeSummary"
import { SkillsEditor } from "./SkillsEditor"

type OnboardingState = ReturnType<typeof useProfileOnboarding>

/** The parsed-resume card: all editable sections, plus the project edit dialog. */
export function ProfileForm({ state }: { state: OnboardingState }) {
  const [openProject, setOpenProject] = useState<Project | null>(null)

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-brand-border bg-white p-6 shadow-[0_4px_20px_rgba(35,31,28,0.04)]">
      <header className="flex items-center justify-between border-b border-brand-border pb-3">
        <h2 className="flex items-center gap-2 font-display text-2xl font-semibold text-brand-ink">
          <Check className="size-5 text-brand-emerald" /> Resume parsed successfully
        </h2>
        <button
          type="button"
          onClick={state.reupload}
          className="inline-flex items-center gap-1 rounded px-2 py-1 font-mono text-[11px] uppercase text-brand-violet hover:bg-brand-violet/10"
        >
          <RefreshCw className="size-3.5" /> Re-upload
        </button>
      </header>

      <IdentityFields identity={state.identity} onChange={state.setIdentityField} />
      <LinksFields identity={state.identity} onChange={state.setIdentityField} />
      <SkillsEditor skills={state.skills} onAdd={state.addSkill} onRemove={state.removeSkill} />
      <ResumeSummary summary={state.summary} onChange={state.setSummaryText} />
      <ProjectList projects={state.projects} onOpen={setOpenProject} onRemove={state.removeProject} />

      {openProject && (
        <ProjectDialog
          key={openProject.project_id}
          project={openProject}
          onClose={() => setOpenProject(null)}
          onSave={(patch) => state.updateProject(openProject.project_id, patch)}
        />
      )}
    </div>
  )
}
