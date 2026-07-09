"use client"

import { useEffect, useState } from "react"
import { X } from "lucide-react"

import type { Project } from "@/lib/api/types"
import { Field } from "./Field"

interface ProjectDialogProps {
  project: Project
  onClose: () => void
  onSave: (patch: Partial<Project>) => void
}

const inputClass =
  "w-full border-none bg-transparent p-0 text-base text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0"

/**
 * Modal to view and edit a project's full details. Edits apply on Done and are
 * persisted with the profile. Mount with `key={project.project_id}` so switching
 * projects resets the draft.
 */
export function ProjectDialog({ project, onClose, onSave }: ProjectDialogProps) {
  const [name, setName] = useState(project.name)
  const [summary, setSummary] = useState(project.summary ?? "")
  const [tech, setTech] = useState((project.tech_stack ?? []).join(", "))
  const [github, setGithub] = useState(project.github_url ?? "")
  const [live, setLive] = useState(project.deployed_url ?? "")

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const done = () => {
    onSave({
      name: name.trim() || project.name,
      summary: summary.trim() || null,
      tech_stack: tech
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      github_url: github.trim() || null,
      deployed_url: live.trim() || null,
    })
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-brand-ink/40 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-lg rounded-2xl border border-brand-border bg-white p-6 shadow-xl"
      >
        <header className="mb-4 flex items-center justify-between">
          <h3 className="font-display text-xl font-semibold text-brand-ink">Edit project</h3>
          <button type="button" onClick={onClose} aria-label="Close" className="text-brand-muted hover:text-brand-ink">
            <X className="size-5" />
          </button>
        </header>

        <div className="flex flex-col gap-4">
          <Field label="Name">
            <input value={name} onChange={(e) => setName(e.target.value)} className={inputClass} />
          </Field>
          <Field label="Summary">
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              rows={4}
              placeholder="What is this project?"
              className={`${inputClass} resize-none`}
            />
          </Field>
          <Field label="Tech (comma-separated)">
            <input value={tech} onChange={(e) => setTech(e.target.value)} placeholder="React, Node.js" className={inputClass} />
          </Field>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="GitHub URL">
              <input value={github} onChange={(e) => setGithub(e.target.value)} placeholder="github.com/…" className={inputClass} />
            </Field>
            <Field label="Live URL">
              <input value={live} onChange={(e) => setLive(e.target.value)} placeholder="myapp.com" className={inputClass} />
            </Field>
          </div>
        </div>

        <footer className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-4 py-2 text-sm font-medium text-brand-muted hover:text-brand-ink"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={done}
            className="rounded-full bg-brand-violet px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-violet-dark"
          >
            Done
          </button>
        </footer>
      </div>
    </div>
  )
}
