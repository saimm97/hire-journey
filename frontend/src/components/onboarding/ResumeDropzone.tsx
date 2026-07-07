"use client"

import { useRef, useState } from "react"
import { Loader2, UploadCloud } from "lucide-react"

import { cn } from "@/lib/utils"

interface ResumeDropzoneProps {
  onFile: (file: File) => void
  parsing: boolean
}

/** Drag-or-click upload area; also the parsing state while the CV is read. */
export function ResumeDropzone({ onFile, parsing }: ResumeDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const pick = (files: FileList | null) => {
    const file = files?.[0]
    if (file) onFile(file)
  }

  return (
    <div
      onClick={() => !parsing && inputRef.current?.click()}
      onDragOver={(event) => {
        event.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        if (!parsing) pick(event.dataTransfer.files)
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed bg-white p-12 text-center shadow-[0_4px_20px_rgba(35,31,28,0.04)] transition-colors",
        dragging ? "border-brand-violet bg-brand-violet/5" : "border-brand-border hover:border-brand-violet/60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(event) => pick(event.target.files)}
      />
      <div className="flex size-16 items-center justify-center rounded-full bg-brand-violet/10 text-brand-violet">
        {parsing ? <Loader2 className="size-8 animate-spin" /> : <UploadCloud className="size-8" />}
      </div>
      <div className="space-y-1">
        <h3 className="font-display text-2xl font-semibold text-brand-ink">
          {parsing ? "Reading your resume…" : "Drop your resume to get started"}
        </h3>
        <p className="text-brand-muted">
          {parsing
            ? "We're extracting your details."
            : "We'll read it and fill in the details — you can fix anything."}
        </p>
      </div>
      {!parsing && (
        <span className="rounded-full bg-brand-coral px-5 py-2.5 font-semibold text-white shadow-sm transition-colors hover:bg-brand-coral-dark">
          Upload resume
        </span>
      )}
      <span className="font-mono text-[11px] uppercase tracking-wide text-brand-muted">
        PDF, DOCX up to 5MB
      </span>
    </div>
  )
}
