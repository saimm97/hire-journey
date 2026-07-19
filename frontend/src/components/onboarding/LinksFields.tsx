"use client"

import type { SocialLinksState } from "@/hooks/useOnboardingProfile"
import { TextField } from "./TextField"

interface LinksFieldsProps {
  links: SocialLinksState
  onChange: (key: keyof SocialLinksState, value: string) => void
}

/** The profile's social links (github / linkedin / portfolio). */
export function LinksFields({ links, onChange }: LinksFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <TextField
        label="GitHub"
        value={links.github_url}
        onChange={(value) => onChange("github_url", value)}
        placeholder="github.com/you"
        mono
      />
      <TextField
        label="LinkedIn"
        value={links.linkedin_url}
        onChange={(value) => onChange("linkedin_url", value)}
        placeholder="linkedin.com/in/you"
        mono
      />
      <TextField
        label="Portfolio"
        value={links.portfolio_url}
        onChange={(value) => onChange("portfolio_url", value)}
        placeholder="you.dev"
        mono
      />
    </div>
  )
}
