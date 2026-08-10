"use client"

import type { SocialLinksState } from "@/lib/onboarding/profileDraft"
import { TextField } from "./TextField"

interface LinksFieldsProps {
  links: SocialLinksState
  onChange: (key: keyof SocialLinksState, value: string) => void
  fieldError: (path: string) => string | undefined
}

/** The profile's social links (github / linkedin / portfolio). */
export function LinksFields({ links, onChange, fieldError }: LinksFieldsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <TextField
        label="GitHub"
        value={links.github_url}
        onChange={(value) => onChange("github_url", value)}
        placeholder="github.com/you"
        mono
        fieldPath="social_links.github_url"
        error={fieldError("social_links.github_url")}
      />
      <TextField
        label="LinkedIn"
        value={links.linkedin_url}
        onChange={(value) => onChange("linkedin_url", value)}
        placeholder="linkedin.com/in/you"
        mono
        fieldPath="social_links.linkedin_url"
        error={fieldError("social_links.linkedin_url")}
      />
      <TextField
        label="Portfolio"
        value={links.portfolio_url}
        onChange={(value) => onChange("portfolio_url", value)}
        placeholder="you.dev"
        mono
        fieldPath="social_links.portfolio_url"
        error={fieldError("social_links.portfolio_url")}
      />
    </div>
  )
}
