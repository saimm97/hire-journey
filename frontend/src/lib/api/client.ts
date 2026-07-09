import { API_BASE_URL, getAuthToken } from "@/lib/env"

/** A failed HTTP call, carrying the status and a user-facing message. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

/** Friendly fallbacks per status; the backend's `detail` string wins when present. */
const STATUS_MESSAGE: Record<number, string> = {
  0: "Can't reach the server. Check your connection and try again.",
  401: "Your session has expired. Sign in again.",
  413: "That file's over 5MB. Try a smaller PDF or DOCX.",
  415: "That needs to be a PDF or DOCX.",
  422: "We couldn't read that file. Try another export.",
  502: "The parser is unavailable right now. Try again in a moment.",
}

async function messageFor(response: Response): Promise<string> {
  const fallback = STATUS_MESSAGE[response.status] ?? "Something went wrong. Try again."
  try {
    const data = await response.json()
    return typeof data?.detail === "string" ? data.detail : fallback
  } catch {
    return fallback
  }
}

interface RequestOptions {
  method?: string
  json?: unknown
  form?: FormData
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers()
  const token = getAuthToken()
  if (token) headers.set("Authorization", `Bearer ${token}`)

  let body: BodyInit | undefined
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json")
    body = JSON.stringify(options.json)
  } else if (options.form) {
    body = options.form
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
    })
  } catch {
    throw new ApiError(0, STATUS_MESSAGE[0])
  }

  if (!response.ok) throw new ApiError(response.status, await messageFor(response))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  patch: <T>(path: string, json: unknown) => request<T>(path, { method: "PATCH", json }),
  put: <T>(path: string, json: unknown) => request<T>(path, { method: "PUT", json }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", form }),
}
