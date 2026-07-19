"use client"

import type { EditableEmployment, ListController } from "@/hooks/useOnboardingProfile"
import { AddItemButton, EditorCard } from "./EditorCard"
import { Field } from "./Field"
import { TextField } from "./TextField"

/** Repeatable editor for the profile's employment history. */
export function EmploymentEditor({
  controller,
}: {
  controller: ListController<EditableEmployment>
}) {
  return (
    <div className="space-y-3">
      {controller.items.map((item, index) => (
        <EditorCard key={index} onRemove={() => controller.remove(index)}>
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <TextField
              label="Company"
              value={item.company_name}
              onChange={(value) => controller.update(index, { company_name: value })}
            />
            <TextField
              label="Title"
              value={item.title}
              onChange={(value) => controller.update(index, { title: value })}
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
          <Field label="What you did" className="mr-8">
            <textarea
              value={item.description}
              onChange={(event) => controller.update(index, { description: event.target.value })}
              rows={2}
              placeholder="Key work and achievements…"
              className="w-full resize-none border-none bg-transparent p-0 text-base leading-relaxed text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0"
            />
          </Field>
        </EditorCard>
      ))}
      <AddItemButton label="Add employment" onClick={controller.add} />
      <p className="text-xs text-brand-muted">Leave “To” empty for your current position.</p>
    </div>
  )
}
