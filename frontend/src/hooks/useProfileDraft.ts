"use client"

import { useCallback, useState, type Dispatch, type SetStateAction } from "react"

import type { FieldErrors } from "@/lib/api/fieldErrors"
import type { OnboardingSnapshot } from "@/lib/api/types"
import {
  EMPTY_DRAFT,
  appendTechnology,
  draftFromSnapshot,
  draftToPayload,
  emptyCertification,
  emptyEducation,
  emptyEmployment,
  emptyProject,
  validateDraft,
  type EditableCertification,
  type EditableEducation,
  type EditableEmployment,
  type EditableProject,
  type Identity,
  type PreparedDetails,
  type ProfileDraft,
  type SocialLinksState,
} from "@/lib/onboarding/profileDraft"

/** The add/update/remove surface every repeatable editor needs. */
export interface ListController<T> {
  items: T[]
  add: () => void
  update: (index: number, patch: Partial<T>) => void
  remove: (index: number) => void
  fieldPath: (index: number, field: keyof T) => string
  fieldError: (index: number, field: keyof T) => string | undefined
  rowError: (index: number) => string | undefined
}

const isProjectErrorPath = (path: string): boolean =>
  path === "projects" || path.startsWith("projects.")

/** Move focus to the control the first error names, once React has painted it. */
function focusFirstError(errors: FieldErrors): void {
  if (typeof document === "undefined") return
  const firstPath = Object.keys(errors)[0]
  if (!firstPath) return
  const schedule =
    window.requestAnimationFrame ??
    ((callback: FrameRequestCallback) => window.setTimeout(callback, 0))
  schedule(() => {
    const field = Array.from(
      document.querySelectorAll<HTMLElement>("[data-field-path]"),
    ).find((element) => element.dataset.fieldPath === firstPath)
    field?.focus()
  })
}

/** Which draft collections a list controller can drive. */
type ListSection = "education" | "certifications" | "employment" | "projects"

/**
 * A repeatable-section view over one slice of the draft. The rows live in the
 * single draft state, so this owns no state of its own — only the edit rules
 * (including which field errors an edit invalidates).
 */
function useListController<T>(
  section: ListSection,
  pathPrefix: string,
  makeEmpty: () => T,
  items: T[],
  setDraft: Dispatch<SetStateAction<ProfileDraft>>,
  fieldErrors: FieldErrors,
  setFieldErrors: Dispatch<SetStateAction<FieldErrors>>,
): ListController<T> {
  const setItems = useCallback(
    (update: (rows: T[]) => T[]) =>
      setDraft((prev) => ({ ...prev, [section]: update(prev[section] as T[]) })),
    [section, setDraft],
  )
  const fieldPath = useCallback(
    (index: number, field: keyof T) => `${pathPrefix}.${index}.${String(field)}`,
    [pathPrefix],
  )
  return {
    items,
    fieldPath,
    add: useCallback(() => setItems((rows) => [...rows, makeEmpty()]), [makeEmpty, setItems]),
    update: useCallback(
      (index: number, patch: Partial<T>) => {
        setItems((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)))
        setFieldErrors((prev) => {
          const next = { ...prev }
          delete next[`${pathPrefix}.${index}`]
          for (const field of Object.keys(patch)) {
            delete next[`${pathPrefix}.${index}.${field}`]
          }
          return next
        })
      },
      [pathPrefix, setItems, setFieldErrors],
    ),
    remove: useCallback(
      (index: number) => {
        setItems((rows) => rows.filter((_, i) => i !== index))
        // Removing a row shifts every following index, so discard the section's
        // stale server paths rather than highlighting the wrong entry.
        setFieldErrors((prev) =>
          Object.fromEntries(
            Object.entries(prev).filter(([path]) => !path.startsWith(`${pathPrefix}.`)),
          ),
        )
      },
      [pathPrefix, setItems, setFieldErrors],
    ),
    fieldError: (index, field) => fieldErrors[fieldPath(index, field)],
    rowError: (index) => fieldErrors[`${pathPrefix}.${index}`],
  }
}

export interface ProfileDraftOptions {
  /** Called when prepareSave rejects a draft, with the number of bad fields. */
  onInvalid?: (fieldCount: number) => void
}

/**
 * Holds the editable details draft and the field errors that address it.
 *
 * The whole draft is one state value, so seeding it from a snapshot is a single
 * assignment and preparing a save has a single dependency. Rules themselves live
 * in `@/lib/onboarding/profileDraft`; this adds only React state and the
 * error-invalidation that editing implies.
 */
export function useProfileDraft({ onInvalid }: ProfileDraftOptions = {}) {
  const [draft, setDraft] = useState<ProfileDraft>(EMPTY_DRAFT)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

  const clearFieldError = useCallback((path: string) => {
    setFieldErrors((prev) => {
      if (!(path in prev)) return prev
      const next = { ...prev }
      delete next[path]
      return next
    })
  }, [])

  const education = useListController<EditableEducation>(
    "education",
    "education",
    emptyEducation,
    draft.education,
    setDraft,
    fieldErrors,
    setFieldErrors,
  )
  const certifications = useListController<EditableCertification>(
    "certifications",
    "certifications",
    emptyCertification,
    draft.certifications,
    setDraft,
    fieldErrors,
    setFieldErrors,
  )
  const employment = useListController<EditableEmployment>(
    "employment",
    "employment_history",
    emptyEmployment,
    draft.employment,
    setDraft,
    fieldErrors,
    setFieldErrors,
  )
  const projects = useListController<EditableProject>(
    "projects",
    "projects",
    emptyProject,
    draft.projects,
    setDraft,
    fieldErrors,
    setFieldErrors,
  )

  const setIdentityField = useCallback(
    (key: keyof Identity, value: string) => {
      setDraft((prev) => ({ ...prev, identity: { ...prev.identity, [key]: value } }))
      clearFieldError(key)
    },
    [clearFieldError],
  )

  const setSocialLink = useCallback(
    (key: keyof SocialLinksState, value: string) => {
      setDraft((prev) => ({ ...prev, socialLinks: { ...prev.socialLinks, [key]: value } }))
      clearFieldError(`social_links.${key}`)
    },
    [clearFieldError],
  )

  const setSummary = useCallback(
    (value: string) => {
      setDraft((prev) => ({ ...prev, summary: value }))
      clearFieldError("summary")
    },
    [clearFieldError],
  )

  const addTechnology = useCallback(
    (value: string) => {
      // Guard here as well as in appendTechnology: a blank chip must not clear
      // a server-side technologies error.
      if (!value.trim()) return
      setDraft((prev) => ({ ...prev, technologies: appendTechnology(prev.technologies, value) }))
      clearFieldError("technologies")
    },
    [clearFieldError],
  )

  const removeTechnology = useCallback(
    (value: string) => {
      setDraft((prev) => ({
        ...prev,
        technologies: prev.technologies.filter((t) => t !== value),
      }))
      clearFieldError("technologies")
    },
    [clearFieldError],
  )

  /** Seed the whole draft from a saved snapshot, discarding any errors. */
  const replaceFromSnapshot = useCallback((snapshot: OnboardingSnapshot) => {
    setDraft(draftFromSnapshot(snapshot))
    setFieldErrors({})
  }, [])

  /** Swap only the projects section, keeping every other unsaved edit. */
  const replaceProjects = useCallback((rows: EditableProject[]) => {
    setDraft((prev) => ({ ...prev, projects: rows }))
    setFieldErrors((prev) =>
      Object.fromEntries(Object.entries(prev).filter(([path]) => !isProjectErrorPath(path))),
    )
  }, [])

  /** Put server-reported errors on the controls they name. */
  const applyServerErrors = useCallback((errors: FieldErrors) => {
    setFieldErrors(errors)
    focusFirstError(errors)
  }, [])

  /**
   * Validate and build the complete details payload, or null after surfacing
   * the inline errors. Split from submitting so the profile editor can send
   * this section together with preferences in one atomic PATCH.
   */
  const prepareSave = useCallback((): PreparedDetails | null => {
    const invalid = validateDraft(draft)
    if (Object.keys(invalid).length) {
      setFieldErrors(invalid)
      onInvalid?.(Object.keys(invalid).length)
      focusFirstError(invalid)
      return null
    }
    setFieldErrors({})
    return draftToPayload(draft)
  }, [draft, onInvalid])

  return {
    identity: draft.identity,
    setIdentityField,
    socialLinks: draft.socialLinks,
    setSocialLink,
    summary: draft.summary,
    setSummary,
    technologies: draft.technologies,
    addTechnology,
    removeTechnology,
    education,
    certifications,
    employment,
    projects,
    fieldErrors,
    fieldError: (path: string) => fieldErrors[path],
    replaceFromSnapshot,
    replaceProjects,
    applyServerErrors,
    prepareSave,
  }
}

export type ProfileDraftState = ReturnType<typeof useProfileDraft>
