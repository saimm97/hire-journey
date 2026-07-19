"use client"

import type { EditableEducation, ListController } from "@/hooks/useOnboardingProfile"
import { AddItemButton, EditorCard } from "./EditorCard"
import { TextField } from "./TextField"

/** Repeatable editor for the profile's education entries. */
export function EducationEditor({ controller }: { controller: ListController<EditableEducation> }) {
  return (
    <div className="space-y-3">
      {controller.items.map((item, index) => (
        <EditorCard key={index} onRemove={() => controller.remove(index)}>
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <TextField
              label="Institution"
              value={item.institution}
              onChange={(value) => controller.update(index, { institution: value })}
            />
            <TextField
              label="Degree"
              value={item.degree}
              onChange={(value) => controller.update(index, { degree: value })}
            />
            <TextField
              label="Field of study"
              value={item.field}
              onChange={(value) => controller.update(index, { field: value })}
            />
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="From"
                type="month"
                mono
                value={item.start_date}
                onChange={(value) => controller.update(index, { start_date: value })}
              />
              <TextField
                label="To"
                type="month"
                mono
                value={item.end_date}
                onChange={(value) => controller.update(index, { end_date: value })}
              />
            </div>
          </div>
        </EditorCard>
      ))}
      <AddItemButton label="Add education" onClick={controller.add} />
    </div>
  )
}
