import { ApiError } from './client'

/** Field errors keyed by a dotted path, e.g. { 'education.0.start_date': '…' }. */
export type FieldErrors = Record<string, string>

export const pathKey = (path: Array<string | number>): string => path.join('.')

export interface FieldErrorOptions {
  /** Drop this leading segment: a form editing one PATCH section uses local paths. */
  section?: string
  /**
   * Rewrite a path after the section is stripped — used where payload indices
   * differ from the rows on screen. MUST return a new array; the caller's
   * ApiError is shared and must never be mutated.
   */
  remapPath?: (path: Array<string | number>) => Array<string | number>
}

/**
 * Flatten structured fields into a path-keyed map (first wins). Both the
 * first-wins rule and the insertion order matter: callers focus the first key,
 * so this must stay a `for…of` with `??=` rather than an Object.fromEntries map.
 */
export function apiFieldErrors(
  error: ApiError,
  { section, remapPath }: FieldErrorOptions = {},
): FieldErrors {
  const errors: FieldErrors = {}
  for (const field of error.fields) {
    const stripped = section && field.path[0] === section ? field.path.slice(1) : field.path
    if (!stripped.length) continue
    const path = remapPath ? remapPath(stripped) : stripped
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
