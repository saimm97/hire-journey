"use client"

import { useEffect } from "react"
import { AlertCircle, CheckCircle2, X } from "lucide-react"

import type { Toast as ToastData } from "@/hooks/useProfileOnboarding"
import { cn } from "@/lib/utils"

interface ToastProps {
  toast: ToastData | null
  onDismiss: () => void
}

/** Bottom-right notification that auto-dismisses. Green for success, red for errors. */
export function Toast({ toast, onDismiss }: ToastProps) {
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(onDismiss, 6000)
    return () => clearTimeout(timer)
  }, [toast, onDismiss])

  if (!toast) return null
  const isError = toast.variant === "error"

  return (
    <div
      role="status"
      className={cn(
        "fixed bottom-24 right-6 z-50 flex max-w-sm items-start gap-3 rounded-lg border-l-4 bg-white p-3 shadow-lg",
        isError ? "border-red-500" : "border-brand-emerald",
      )}
    >
      {isError ? (
        <AlertCircle className="mt-0.5 size-5 shrink-0 text-red-500" />
      ) : (
        <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-brand-emerald" />
      )}
      <p className="text-sm text-brand-ink">{toast.message}</p>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss"
        className="ml-auto text-brand-muted hover:text-brand-ink"
      >
        <X className="size-4" />
      </button>
    </div>
  )
}
