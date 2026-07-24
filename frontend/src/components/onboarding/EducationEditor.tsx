"use client"

import type { EditableEducation, ListController } from "@/hooks/useOnboardingProfile"
import { AddItemButton, EditorCard } from "./EditorCard"
import { TextField } from "./TextField"
import { YearMonthField } from "./YearMonthField"

/** Repeatable editor for the profile's education entries. */
export function EducationEditor({ controller }: { controller: ListController<EditableEducation> }) {
  return (
    <div className="space-y-3">
      {controller.items.map((item, index) => (
        <EditorCard
          key={index}
          onRemove={() => controller.remove(index)}
          error={controller.rowError(index)}
          fieldPath={`education.${index}`}
        >
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <TextField
              label="Institution"
              value={item.institution}
              onChange={(value) => controller.update(index, { institution: value })}
              fieldPath={controller.fieldPath(index, "institution")}
              error={controller.fieldError(index, "institution")}
            />
            <TextField
              label="Degree"
              value={item.degree}
              onChange={(value) => controller.update(index, { degree: value })}
              fieldPath={controller.fieldPath(index, "degree")}
              error={controller.fieldError(index, "degree")}
            />
            <TextField
              label="Field of study"
              value={item.field}
              onChange={(value) => controller.update(index, { field: value })}
              fieldPath={controller.fieldPath(index, "field")}
              error={controller.fieldError(index, "field")}
            />
            <div className="grid grid-cols-2 gap-3">
              <YearMonthField
                label="From"
                value={item.start_date}
                onChange={(value) => controller.update(index, { start_date: value })}
                fieldPath={controller.fieldPath(index, "start_date")}
                error={controller.fieldError(index, "start_date")}
              />
              <YearMonthField
                label="To"
                value={item.end_date}
                onChange={(value) => controller.update(index, { end_date: value })}
                fieldPath={controller.fieldPath(index, "end_date")}
                error={controller.fieldError(index, "end_date")}
              />
            </div>
          </div>
        </EditorCard>
      ))}
      <AddItemButton label="Add education" onClick={controller.add} />
    </div>
  )
}
