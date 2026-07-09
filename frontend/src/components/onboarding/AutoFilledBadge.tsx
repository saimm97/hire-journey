import { Sparkles } from "lucide-react"

/** Small marker showing a value came from the parsed CV. */
export function AutoFilledBadge({ label = "Auto-filled" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded bg-brand-violet/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-brand-violet">
      <Sparkles className="size-2.5" /> {label}
    </span>
  )
}
