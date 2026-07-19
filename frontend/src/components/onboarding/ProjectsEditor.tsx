"use client"

import type { EditableProject, ListController } from "@/hooks/useOnboardingProfile"
import { AddItemButton, EditorCard } from "./EditorCard"
import { ChipInput } from "./ChipInput"
import { Field } from "./Field"
import { TextField } from "./TextField"

/** Repeatable editor for the profile's projects (inline, no dialog). */
export function ProjectsEditor({ controller }: { controller: ListController<EditableProject> }) {
  const addTechnology = (index: number, item: EditableProject, value: string) => {
    const technology = value.trim()
    if (!technology) return
    if (item.technologies.some((t) => t.toLowerCase() === technology.toLowerCase())) return
    controller.update(index, { technologies: [...item.technologies, technology] })
  }

  return (
    <div className="space-y-3">
      {controller.items.map((item, index) => (
        <EditorCard key={item.project_id ?? `new-${index}`} onRemove={() => controller.remove(index)}>
          <div className="grid gap-3 pr-8 sm:grid-cols-2">
            <TextField
              label="Name"
              value={item.name}
              onChange={(value) => controller.update(index, { name: value })}
              className="sm:col-span-2"
            />
            <TextField
              label="GitHub URL"
              value={item.github_url}
              onChange={(value) => controller.update(index, { github_url: value })}
              placeholder="github.com/you/project"
              mono
            />
            <TextField
              label="Live URL"
              value={item.deployed_url}
              onChange={(value) => controller.update(index, { deployed_url: value })}
              placeholder="project.dev"
              mono
            />
          </div>
          <Field label="Summary" className="mr-8">
            <textarea
              value={item.summary}
              onChange={(event) => controller.update(index, { summary: event.target.value })}
              rows={3}
              placeholder="What it does, how it's built…"
              className="w-full resize-none border-none bg-transparent p-0 text-base leading-relaxed text-brand-ink outline-none placeholder:text-brand-muted/60 focus:ring-0"
            />
          </Field>
          <div className="mr-8">
            <ChipInput
              layout="inline"
              values={item.technologies}
              onAdd={(value) => addTechnology(index, item, value)}
              onRemove={(value) =>
                controller.update(index, {
                  technologies: item.technologies.filter((t) => t !== value),
                })
              }
              placeholder="Add tech"
              addLabel="Add technology"
            />
          </div>
        </EditorCard>
      ))}
      <AddItemButton label="Add project" onClick={controller.add} />
    </div>
  )
}
