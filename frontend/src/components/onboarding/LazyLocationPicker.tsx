"use client"

import dynamic from "next/dynamic"
import { Loader2 } from "lucide-react"

/** country-state-city bundles a large dataset — keep it in a lazy async chunk. */
export const LazyLocationPicker = dynamic(() => import("./LocationPicker"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center gap-2 py-2 text-sm text-brand-muted">
      <Loader2 className="size-4 animate-spin" /> Loading locations…
    </div>
  ),
})
