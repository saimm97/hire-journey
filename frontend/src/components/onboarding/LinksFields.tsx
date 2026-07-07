"use client"

import type { Identity } from "@/hooks/useProfileOnboarding"
import { Section } from "./Section"
import { TextField } from "./TextField"

interface LinksFieldsProps {
  identity: Identity
  onChange: (key: keyof Identity, value: string) => void
}

/** GitHub and portfolio URLs (stored as candidate columns, not free-form chips). */
export function LinksFields({ identity, onChange }: LinksFieldsProps) {
  return (
    <Section title="Links">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <TextField
          label="GitHub URL"
          type="url"
          placeholder="github.com/you"
          value={identity.github_url}
          onChange={(v) => onChange("github_url", v)}
        />
        <TextField
          label="Portfolio URL"
          type="url"
          placeholder="you.dev"
          value={identity.portfolio_url}
          onChange={(v) => onChange("portfolio_url", v)}
        />
      </div>
    </Section>
  )
}
