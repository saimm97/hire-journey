const BASE_URL = process.env.NEXT_PUBLIC_API_URL

/** Error thrown for any non-2xx response, carrying the backend's status + detail. */
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  method?: string
  body?: unknown
  form?: boolean
}

/**
 * Single entry point for every backend call. Prepends the API base + version,
 * and normalizes errors so callers only ever deal with `ApiError`.
 */
export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = 'GET', body, form = false } = options

  const headers: Record<string, string> = {}

  let payload: BodyInit | undefined
  if (body !== undefined) {
    if (form) {
      headers['Content-Type'] = 'application/x-www-form-urlencoded'
      payload = new URLSearchParams(body as Record<string, string>).toString()
    } else {
      headers['Content-Type'] = 'application/json'
      payload = JSON.stringify(body)
    }
  }

  const res = await fetch(`${BASE_URL}/api/v1${path}`, {
    method,
    headers,
    body: payload,
    credentials: 'include',
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      // error body wasn't JSON; keep the status text
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}
