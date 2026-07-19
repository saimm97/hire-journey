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
}

/** Name, contact, and professional-title fields, plus the read-only account email. */
export function IdentityFields({ identity, accountEmail, onChange }: IdentityFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <TextField
        label="First name"
        value={identity.first_name}
        onChange={(value) => onChange("first_name", value)}
      />
      <TextField
        label="Last name"
        value={identity.last_name}
        onChange={(value) => onChange("last_name", value)}
      />
      <TextField
        label="Phone"
        value={identity.phone_number}
        onChange={(value) => onChange("phone_number", value)}
        type="tel"
        mono
      />
      <TextField
        label="Title"
        value={identity.title}
        onChange={(value) => onChange("title", value)}
        placeholder="e.g. Backend Engineer"
      />
      <div className="space-y-2 sm:col-span-2">
        <Field label="Location">
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
        className="bg-brand-surface sm:col-span-2"
      >
        <p className="text-base text-brand-muted">{accountEmail}</p>
      </Field>
    </div>
  )
}
