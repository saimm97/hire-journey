"use client"

import { AutoFilledBadge } from "./AutoFilledBadge"
import { Section } from "./Section"

interface ResumeSummaryProps {
  summary: string | null
  onChange: (value: string) => void
}

/** Editable professional summary; the badge marks it as parsed when it has content. */
export function ResumeSummary({ summary, onChange }: ResumeSummaryProps) {
  return (
    <Section
      title="Professional summary"
      action={summary ? <AutoFilledBadge label="Parsed from CV" /> : undefined}
    >
      <textarea
        value={summary ?? ""}
        onChange={(event) => onChange(event.target.value)}
        rows={4}
        placeholder="Add a short professional summary…"
        className="w-full resize-none rounded-lg border border-brand-border bg-white p-3 text-base leading-relaxed text-brand-ink outline-none transition-all placeholder:text-brand-muted/60 focus:border-brand-primary focus:ring-2 focus:ring-brand-primary/20"
      />
    </Section>
  )
}
