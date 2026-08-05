import { ApiError } from './client'

/** Field errors keyed by a dotted path, e.g. { 'education.0.start_date': '…' }. */
export type FieldErrors = Record<string, string>

export const pathKey = (path: Array<string | number>): string => path.join('.')

/**
 * Flatten structured fields into a path-keyed map (first wins). When a form
 * edits one PATCH section, omit that section prefix from its local field paths.
 */
export function apiFieldErrors(error: ApiError, section?: string): FieldErrors {
  const errors: FieldErrors = {}
  for (const field of error.fields) {
    const path = section && field.path[0] === section ? field.path.slice(1) : field.path
    if (!path.length) continue
    errors[pathKey(path)] ??= field.message
  }
  return errors
}

/**
 * Error for an exact path, or the first nested one under it. Group controls
 * (a work-mode toggle set) can't address `work_modes_preferred.0`, so they look
 * up the whole `work_modes_preferred` group and surface whatever landed inside.
 */
export function groupError(errors: FieldErrors, prefix: string): string | undefined {
  return (
    errors[prefix] ?? Object.entries(errors).find(([key]) => key.startsWith(`${prefix}.`))?.[1]
  )
}
