const BASE_URL = process.env.NEXT_PUBLIC_API_URL

/** Last-resort message when the server sends nothing we can render. */
const FALLBACK_MESSAGE = "We couldn't complete that. Please try again."

/** One actionable, field-level issue. `path` mirrors the backend location, e.g.
 * ['education', 0, 'start_date'] — the leading 'body' segment is already stripped. */
export type ApiFieldError = {
  path: Array<string | number>
  message: string
}

/**
 * Error thrown for any non-2xx response. Carries a safe `message` for toasts,
 * a machine-readable `code`, and `fields` for inline per-input errors. The
 * `message` is ALWAYS a string — objects never reach the Error constructor,
 * which is what previously produced the "[object Object]" toast.
 */
export class ApiError extends Error {
  status: number
  code: string
  fields: ApiFieldError[]
  requestId?: string

  constructor(
    status: number,
    init: { message: string; code?: string; fields?: ApiFieldError[]; requestId?: string },
  ) {
    super(init.message)
    this.name = 'ApiError'
    this.status = status
    this.code = init.code ?? 'error'
    this.fields = init.fields ?? []
    this.requestId = init.requestId
  }

  /** The message for a specific field path, or undefined. Compares by joined path. */
  fieldError(path: Array<string | number>): string | undefined {
    const key = path.join('.')
    return this.fields.find((f) => f.path.join('.') === key)?.message
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
  form?: boolean
  /** Abort and reject after this many ms so a stalled backend can't wedge the UI. */
  timeoutMs?: number
}

/** Default request ceiling. CV upload runs LLM extraction, so it passes a larger one. */
const DEFAULT_TIMEOUT_MS = 30_000

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const LOCATION_PREFIXES = new Set(['body', 'query', 'path', 'header', 'cookie'])

/** Turn one Pydantic error entry ({loc, msg, type}) into our field shape. */
function fromPydantic(entry: unknown): ApiFieldError | null {
  if (!isRecord(entry) || !Array.isArray(entry.loc)) return null
  // Drop the leading "body"/"query"/"path" segment — it's transport noise the
  // user shouldn't see; what remains addresses the actual field.
  const rawPath = entry.loc.filter(
    (part): part is string | number => typeof part === 'string' || typeof part === 'number',
  )
  const path =
    typeof rawPath[0] === 'string' && LOCATION_PREFIXES.has(rawPath[0])
      ? rawPath.slice(1)
      : rawPath
  const raw = typeof entry.msg === 'string' ? entry.msg : 'is invalid'
  // Pydantic prefixes custom ValueErrors with "Value error, "; strip it.
  const message = raw.replace(/^Value error,\s*/i, '')
  return { path, message }
}

function parseFields(value: unknown): ApiFieldError[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    if (!isRecord(item)) return []
    const path = Array.isArray(item.path)
      ? item.path.filter(
          (part): part is string | number =>
            typeof part === 'string' || typeof part === 'number',
        )
      : []
    const message = typeof item.message === 'string' ? item.message : ''
    return message ? [{ path, message }] : []
  })
}

/**
 * Normalize any error response into an ApiError. Supports, in order:
 *   1. The new envelope: { error: { code, message, fields, request_id } }
 *   2. Legacy FastAPI string detail: { detail: "..." }
 *   3. Legacy FastAPI validation array: { detail: [ {loc, msg, type}, ... ] }
 *   4. Non-JSON / unknown bodies -> a safe fallback string.
 * It never assigns a non-string to Error.message.
 */
async function toApiError(res: Response, signal?: AbortSignal): Promise<ApiError> {
  let body: unknown
  try {
    body = await res.json()
  } catch (error) {
    // Let the outer request boundary classify an abort as a timeout. Otherwise
    // a stalled error body would be mistaken for an ordinary non-JSON response.
    if (signal?.aborted) throw error
    return new ApiError(res.status, { message: res.statusText || FALLBACK_MESSAGE })
  }

  // 1. New envelope.
  if (isRecord(body) && isRecord(body.error)) {
    const err = body.error
    return new ApiError(res.status, {
      message: typeof err.message === 'string' ? err.message : FALLBACK_MESSAGE,
      code: typeof err.code === 'string' ? err.code : undefined,
      fields: parseFields(err.fields),
      requestId: typeof err.request_id === 'string' ? err.request_id : undefined,
    })
  }

  // 2. Legacy string detail (custom HTTPExceptions).
  if (isRecord(body) && typeof body.detail === 'string') {
    return new ApiError(res.status, { message: body.detail })
  }

  // 3. Legacy validation array (Pydantic RequestValidationError) — the shape
  // that used to become "[object Object]". Flatten into field errors.
  if (isRecord(body) && Array.isArray(body.detail)) {
    const fields = body.detail.map(fromPydantic).filter((f): f is ApiFieldError => f !== null)
    return new ApiError(res.status, {
      code: 'validation_error',
      message: fields.length ? 'Some details need fixing.' : FALLBACK_MESSAGE,
      fields,
    })
  }

  // 4. Anything else.
  return new ApiError(res.status, { message: res.statusText || FALLBACK_MESSAGE })
}

/**
 * Single entry point for every backend call. Prepends the API base + version,
 * and normalizes errors so callers only ever deal with `ApiError`.
 */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, form = false, timeoutMs = DEFAULT_TIMEOUT_MS } = options

  const headers: Record<string, string> = {}

  let payload: BodyInit | undefined
  if (body !== undefined) {
    if (body instanceof FormData) {
      // Multipart upload — the browser sets the Content-Type boundary itself.
      payload = body
    } else if (form) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
      payload = new URLSearchParams(body as Record<string, string>).toString()
    } else {
      headers['Content-Type'] = 'application/json'
      payload = JSON.stringify(body)
    }
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(`${BASE_URL}/api/v1${path}`, {
      method,
      headers,
      body: payload,
      credentials: 'include',
      signal: controller.signal,
    })

    if (!res.ok) {
      throw await toApiError(res, controller.signal)
    }

    if (res.status === 204) return undefined as T
    try {
      // Keep the abort timer alive until the complete body has arrived. fetch()
      // resolves after headers, so clearing it earlier can leave json() hanging.
      return (await res.json()) as T
    } catch (error) {
      if (controller.signal.aborted) throw error
      throw new ApiError(res.status, {
        code: 'invalid_response',
        message: 'The server returned an unexpected response. Please try again.',
      })
    }
  } catch (error) {
    // Structured HTTP/response errors are already safe and actionable.
    if (error instanceof ApiError) throw error
    // A timeout aborts the signal; distinguish it from a genuine network failure
    // so the user knows to retry rather than check their connection.
    if (controller.signal.aborted) {
      throw new ApiError(0, {
        code: 'timeout',
        message: 'This is taking longer than expected. Please try again.',
      })
    }
    throw new ApiError(0, {
      code: 'network_error',
      message: "We couldn't reach the server. Check your connection and try again.",
    })
  } finally {
    clearTimeout(timer)
  }
}
