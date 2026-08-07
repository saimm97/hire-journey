"use client"

import type { ListController } from "@/hooks/useProfileDraft"
import type { EditableCertification } from "@/lib/onboarding/profileDraft"
import { AddItemButton, EditorCard } from "./EditorCard"
import { TextField } from "./TextField"
import { YearMonthField } from "./YearMonthField"

/** Repeatable editor for the profile's certifications. */
export function CertificationEditor({
  controller,
}: {
  controller: ListController<EditableCertification>
}) {
  return (
    <div className="space-y-3">
      {controller.items.map((item, index) => (
        <EditorCard
          key={index}
          onRemove={() => controller.remove(index)}
          error={controller.rowError(index)}
          fieldPath={`certifications.${index}`}
        >
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <TextField
              label="Name"
              value={item.name}
              onChange={(value) => controller.update(index, { name: value })}
              fieldPath={controller.fieldPath(index, "name")}
              error={controller.fieldError(index, "name")}
            />
            <TextField
              label="Issuer"
              value={item.issuer}
              onChange={(value) => controller.update(index, { issuer: value })}
              fieldPath={controller.fieldPath(index, "issuer")}
              error={controller.fieldError(index, "issuer")}
            />
            <div className="grid grid-cols-2 gap-3 sm:col-span-2 sm:max-w-sm">
              <YearMonthField
                label="Issued"
                value={item.issued_at}
                onChange={(value) => controller.update(index, { issued_at: value })}
                fieldPath={controller.fieldPath(index, "issued_at")}
                error={controller.fieldError(index, "issued_at")}
              />
              <YearMonthField
                label="Expires"
                value={item.expires_at}
                onChange={(value) => controller.update(index, { expires_at: value })}
                fieldPath={controller.fieldPath(index, "expires_at")}
                error={controller.fieldError(index, "expires_at")}
              />
            </div>
          </div>
        </EditorCard>
      ))}
      <AddItemButton label="Add certification" onClick={controller.add} />
    </div>
  )
}
