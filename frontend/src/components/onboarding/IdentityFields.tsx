"use client"

import type { Identity } from "@/hooks/useProfileOnboarding"
import { AutoFilledBadge } from "./AutoFilledBadge"
import { Section } from "./Section"
import { TextField } from "./TextField"

interface IdentityFieldsProps {
  identity: Identity
  onChange: (key: keyof Identity, value: string) => void
}

const filled = (value: string) => (value ? <AutoFilledBadge /> : undefined)

/** Editable name and contact details parsed from the CV. */
export function IdentityFields({ identity, onChange }: IdentityFieldsProps) {
  return (
    <Section title="Identity & contact">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <TextField
          label="First name"
          value={identity.first_name}
          onChange={(v) => onChange("first_name", v)}
          badge={filled(identity.first_name)}
        />
        <TextField
          label="Last name"
          value={identity.last_name}
          onChange={(v) => onChange("last_name", v)}
          badge={filled(identity.last_name)}
        />
        <TextField
          label="Email"
          type="email"
          value={identity.email}
          onChange={(v) => onChange("email", v)}
          badge={filled(identity.email)}
        />
        <TextField
          label="Phone"
          type="tel"
          mono
          value={identity.phone}
          onChange={(v) => onChange("phone", v)}
          badge={filled(identity.phone)}
        />
      </div>
    </Section>
  )
}
