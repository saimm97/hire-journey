"use client"

import { Code2, Link2, Pencil, Trash2 } from "lucide-react"

import type { Project } from "@/lib/api/types"
import { Section } from "./Section"

interface ProjectListProps {
  projects: Project[]
  onOpen: (project: Project) => void
  onRemove: (projectId: string) => void
}

/** CV projects as cards. Clicking a card opens it for editing; hidden when empty. */
export function ProjectList({ projects, onOpen, onRemove }: ProjectListProps) {
  if (projects.length === 0) return null
  return (
    <Section title="Projects we found">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {projects.map((project) => (
          <ProjectCard
            key={project.project_id}
            project={project}
            onOpen={() => onOpen(project)}
            onRemove={() => onRemove(project.project_id)}
          />
        ))}
      </div>
    </Section>
  )
}

interface ProjectCardProps {
  project: Project
  onOpen: () => void
  onRemove: () => void
}

function ProjectCard({ project, onOpen, onRemove }: ProjectCardProps) {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault()
          onOpen()
        }
      }}
      title="Click to edit"
      className="group relative cursor-pointer rounded-lg border border-brand-border bg-brand-surface/40 p-3 transition-colors hover:border-brand-violet/40"
    >
      <div className="absolute right-2 top-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
        <Pencil className="size-4 text-brand-muted" />
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation()
            onRemove()
          }}
          aria-label={`Remove ${project.name}`}
          className="text-brand-muted hover:text-red-500"
        >
          <Trash2 className="size-4" />
        </button>
      </div>
      <h4 className="mb-1 pr-12 font-display text-lg font-semibold text-brand-ink">{project.name}</h4>
      {project.summary && <p className="mb-2 line-clamp-2 text-sm text-brand-muted">{project.summary}</p>}
      {project.tech_stack && project.tech_stack.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {project.tech_stack.map((tech) => (
            <span key={tech} className="rounded-sm bg-brand-surface px-1.5 py-0.5 text-[10px] text-brand-muted">
              {tech}
            </span>
          ))}
        </div>
      )}
      <div className="flex items-center gap-3 text-xs text-brand-violet">
        {project.github_url && (
          <a
            href={project.github_url}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex items-center gap-1 hover:underline"
          >
            <Code2 className="size-3.5" /> Code
          </a>
        )}
        {project.deployed_url && (
          <a
            href={project.deployed_url}
            target="_blank"
            rel="noreferrer"
            onClick={(event) => event.stopPropagation()}
            className="inline-flex items-center gap-1 hover:underline"
          >
            <Link2 className="size-3.5" /> Live
          </a>
        )}
        <span className="ml-auto rounded-sm bg-brand-surface px-1.5 py-0.5 font-mono text-[10px] uppercase text-brand-muted">
          from {project.source}
        </span>
      </div>
    </div>
  )
}
