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

  const open = () => !parsing && inputRef.current?.click()

  return (
    <div
      role="button"
      tabIndex={parsing ? -1 : 0}
      aria-label="Upload resume (PDF or DOCX, up to 5MB)"
      aria-disabled={parsing}
      onClick={open}
      onKeyDown={(event) => {
        // Space/Enter activate a button; prevent Space from scrolling the page.
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          open()
        }
      }}
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
        "flex cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed bg-white p-8 text-center transition-colors sm:p-12",
        "focus-visible:border-brand-violet focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-violet/40",
        dragging ? "border-brand-violet bg-brand-violet/5" : "border-brand-border hover:border-brand-violet/60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onClick={(event) => event.stopPropagation()}
        onChange={(event) => {
          pick(event.currentTarget.files)
          // Selecting the same file after a timeout/failure must emit another
          // change event. The File object passed above remains valid.
          event.currentTarget.value = ""
        }}
      />
      <div className="flex size-16 items-center justify-center rounded-full bg-brand-violet/10 text-brand-violet">
        {parsing ? <Loader2 className="size-8 animate-spin" /> : <UploadCloud className="size-8" />}
      </div>
      <div className="space-y-1">
        <h3 className="text-2xl font-semibold tracking-tight text-brand-ink">
          {parsing ? "Reading your resume…" : "Drop your resume to get started"}
        </h3>
        <p className="text-brand-muted">
          {parsing
            ? "We're extracting your details."
            : "We'll read it and fill in the details — you can fix anything."}
        </p>
      </div>
      {!parsing && (
        <span className="rounded-lg bg-brand-violet px-5 py-2.5 font-semibold text-white transition-colors hover:bg-brand-violet-dark">
          Upload resume
        </span>
      )}
      <span className="text-xs text-brand-muted">
        PDF, DOCX up to 5MB
      </span>
    </div>
  )
}
