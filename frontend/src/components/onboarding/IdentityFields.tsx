"use client"

import { Lock } from "lucide-react"

import type { Identity } from "@/hooks/useOnboardingProfile"
import { Field } from "./Field"
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
        label="Location"
        value={identity.location}
        onChange={(value) => onChange("location", value)}
        placeholder="City, Country"
      />
      <TextField
        label="Title"
        value={identity.title}
        onChange={(value) => onChange("title", value)}
        placeholder="e.g. Backend Engineer"
        className="sm:col-span-2"
      />
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
