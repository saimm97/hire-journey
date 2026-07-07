import type { ReactNode } from "react"

interface SectionProps {
  title: string
  action?: ReactNode
  children: ReactNode
}

/** A titled block: a mono uppercase heading with an optional right-aligned action. */
export function Section({ title, action, children }: SectionProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-mono text-[11px] uppercase tracking-wider text-brand-muted">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  )
}
