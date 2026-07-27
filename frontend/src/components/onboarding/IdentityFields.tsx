"use client"

import { Lock, X } from "lucide-react"

import type { Identity } from "@/hooks/useOnboardingProfile"
import { Field } from "./Field"
import { LazyLocationPicker } from "./LazyLocationPicker"
import { TextField } from "./TextField"

interface IdentityFieldsProps {
  identity: Identity
  accountEmail: string
  onChange: (key: keyof Identity, value: string) => void
  fieldError: (path: string) => string | undefined
}

/** Name, contact, and professional-title fields, plus the read-only account email. */
export function IdentityFields({
  identity,
  accountEmail,
  onChange,
  fieldError,
}: IdentityFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TextField
        label="First name"
        value={identity.first_name}
        onChange={(value) => onChange("first_name", value)}
        fieldPath="first_name"
        error={fieldError("first_name")}
      />
      <TextField
        label="Last name"
        value={identity.last_name}
        onChange={(value) => onChange("last_name", value)}
        fieldPath="last_name"
        error={fieldError("last_name")}
      />
      <TextField
        label="Phone"
        value={identity.phone_number}
        onChange={(value) => onChange("phone_number", value)}
        type="tel"
        mono
        fieldPath="phone_number"
        error={fieldError("phone_number")}
      />
      <TextField
        label="Title"
        value={identity.title}
        onChange={(value) => onChange("title", value)}
        placeholder="e.g. Backend Engineer"
        fieldPath="title"
        error={fieldError("title")}
      />
      <div className="space-y-2 sm:col-span-2">
        <Field
          label="Location"
          fieldPath="location"
          error={fieldError("location")}
          errorId="field-location-error"
        >
          {identity.location ? (
            <div className="flex items-center justify-between">
              <span className="text-base text-brand-ink">{identity.location}</span>
              <button
                type="button"
                onClick={() => onChange("location", "")}
                aria-label="Clear location"
                className="text-brand-muted hover:text-brand-ink"
              >
                <X className="size-4" />
              </button>
            </div>
          ) : (
            <p className="text-base text-brand-muted/60">Pick your location below</p>
          )}
        </Field>
        <LazyLocationPicker
          buttonLabel="Set location"
          onSelect={(label) => onChange("location", label)}
        />
      </div>
      <Field
        label="Account email"
        badge={<Lock className="size-3 text-brand-muted" />}
        className="sm:col-span-2"
      >
        <p className="text-base text-brand-muted">{accountEmail}</p>
      </Field>
    </div>
  )
}
