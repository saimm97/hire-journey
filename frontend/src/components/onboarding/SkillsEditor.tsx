"use client"

import { useState } from "react"
import { Plus, X } from "lucide-react"

import { Section } from "./Section"

interface SkillsEditorProps {
  skills: string[]
  onAdd: (skill: string) => void
  onRemove: (skill: string) => void
}

/** Removable skill chips plus an inline add-skill input (maps to tech_stack). */
export function SkillsEditor({ skills, onAdd, onRemove }: SkillsEditorProps) {
  const [draft, setDraft] = useState("")

  const commit = () => {
    onAdd(draft)
    setDraft("")
  }

  return (
    <Section title="Skills & technologies">
      <div className="flex flex-wrap gap-2">
        {skills.map((skill) => (
          <span
            key={skill}
            className="inline-flex items-center gap-1 rounded-full bg-brand-surface px-3 py-1 text-sm text-brand-muted"
          >
            {skill}
            <button
              type="button"
              onClick={() => onRemove(skill)}
              aria-label={`Remove ${skill}`}
              className="flex items-center hover:text-brand-ink"
            >
              <X className="size-3.5" />
            </button>
          </span>
        ))}
        <div className="inline-flex items-center rounded-full border border-brand-border bg-white px-3 py-1 focus-within:border-brand-violet focus-within:ring-2 focus-within:ring-brand-violet/20">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                commit()
              }
            }}
            placeholder="Add skill…"
            className="w-24 border-none bg-transparent p-0 text-sm text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0"
          />
          <button
            type="button"
            onClick={commit}
            aria-label="Add skill"
            className="flex items-center text-brand-muted hover:text-brand-violet"
          >
            <Plus className="size-4" />
          </button>
        </div>
      </div>
    </Section>
  )
}
