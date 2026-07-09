"use client"

import { ChipInput } from "./ChipInput"
import { Section } from "./Section"

interface SkillsEditorProps {
  skills: string[]
  onAdd: (skill: string) => void
  onRemove: (skill: string) => void
}

/** Removable skill chips plus an inline add-skill input (maps to tech_stack). */
export function SkillsEditor({ skills, onAdd, onRemove }: SkillsEditorProps) {
  return (
    <Section title="Skills & technologies">
      <ChipInput
        layout="inline"
        values={skills}
        onAdd={onAdd}
        onRemove={onRemove}
        placeholder="Add skill…"
        addLabel="Add skill"
      />
    </Section>
  )
}
