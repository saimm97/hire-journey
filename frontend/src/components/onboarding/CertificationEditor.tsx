"use client"

import type { EditableCertification, ListController } from "@/hooks/useOnboardingProfile"
import { AddItemButton, EditorCard } from "./EditorCard"
import { TextField } from "./TextField"

/** Repeatable editor for the profile's certifications. */
export function CertificationEditor({
  controller,
}: {
  controller: ListController<EditableCertification>
}) {
  return (
    <div className="space-y-3">
      {controller.items.map((item, index) => (
        <EditorCard key={index} onRemove={() => controller.remove(index)}>
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <TextField
              label="Name"
              value={item.name}
              onChange={(value) => controller.update(index, { name: value })}
            />
            <TextField
              label="Issuer"
              value={item.issuer}
              onChange={(value) => controller.update(index, { issuer: value })}
            />
            <div className="grid grid-cols-2 gap-3 sm:col-span-2 sm:max-w-sm">
              <TextField
                label="Issued"
                type="month"
                mono
                value={item.issued_at}
                onChange={(value) => controller.update(index, { issued_at: value })}
              />
              <TextField
                label="Expires"
                type="month"
                mono
                value={item.expires_at}
                onChange={(value) => controller.update(index, { expires_at: value })}
              />
            </div>
          </div>
        </EditorCard>
      ))}
      <AddItemButton label="Add certification" onClick={controller.add} />
    </div>
  )
}
