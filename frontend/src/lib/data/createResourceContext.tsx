"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react"

export interface Resource<T> {
  /** The cached value, or null before the first load / when absent. */
  data: T | null
  loading: boolean
  error: unknown
  /** Re-fetch from the server — call after a mutation to update every consumer. */
  refresh: () => Promise<void>
  /** Replace the cached value locally without a request (optimistic update). */
  set: (data: T | null) => void
}

/**
 * Build a Provider + hook pair that fetches a resource once, caches it in
 * context, and shares it with every descendant. Reuse for any table:
 *
 *   const { Provider, useResource } = createResourceContext(getOnboarding, "Profile")
 *
 * Mount the Provider in a route layout (not a per-page component) so the cache
 * survives navigation and the fetch runs exactly once per session.
 */
export function createResourceContext<T>(fetcher: () => Promise<T | null>, name: string) {
  const Context = createContext<Resource<T> | null>(null)

  function Provider({ children }: { children: ReactNode }) {
    const [data, setData] = useState<T | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<unknown>(null)

    // Manual refresh — safe to flip loading synchronously since it's called
    // from event handlers, never from an effect.
    const refresh = useCallback(async () => {
      setLoading(true)
      setError(null)
      try {
        setData(await fetcher())
      } catch (err) {
        setError(err)
      } finally {
        setLoading(false)
      }
    }, [])

    // Initial load. State is only touched inside async callbacks, so this
    // never synchronously sets state during the effect.
    useEffect(() => {
      let active = true
      fetcher()
        .then((result) => active && setData(result))
        .catch((err) => active && setError(err))
        .finally(() => active && setLoading(false))
      return () => {
        active = false
      }
    }, [])

    return (
      <Context.Provider value={{ data, loading, error, refresh, set: setData }}>
        {children}
      </Context.Provider>
    )
  }
  Provider.displayName = `${name}Provider`

  function useResource(): Resource<T> {
    const ctx = useContext(Context)
    if (!ctx) throw new Error(`use${name} must be used inside <${name}Provider>`)
    return ctx
  }

  return { Provider, useResource }
}
