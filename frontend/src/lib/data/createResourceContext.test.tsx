import { act, render, renderHook, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

import { createResourceContext } from "./createResourceContext"

describe("createResourceContext", () => {
  it("fetches once and shares the value with every consumer", async () => {
    const fetcher = vi.fn().mockResolvedValue({ name: "Jane" })
    const { Provider, useResource } = createResourceContext(fetcher, "Test")

    function Consumer() {
      const { data, loading } = useResource()
      return <span>{loading ? "loading" : data?.name}</span>
    }

    render(
      <Provider>
        <Consumer />
        <Consumer />
      </Provider>,
    )

    await waitFor(() => expect(screen.getAllByText("Jane")).toHaveLength(2))
    // Two consumers, still a single network call — the point of the cache.
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it("refresh() re-fetches and updates the cache", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce("first").mockResolvedValueOnce("second")
    const { Provider, useResource } = createResourceContext(fetcher, "Test")
    const wrapper = ({ children }: { children: ReactNode }) => <Provider>{children}</Provider>

    const { result } = renderHook(() => useResource(), { wrapper })
    await waitFor(() => expect(result.current.data).toBe("first"))

    await act(async () => {
      await result.current.refresh()
    })
    expect(result.current.data).toBe("second")
    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it("captures a fetch error without throwing", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("boom"))
    const { Provider, useResource } = createResourceContext(fetcher, "Test")
    const wrapper = ({ children }: { children: ReactNode }) => <Provider>{children}</Provider>

    const { result } = renderHook(() => useResource(), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBeInstanceOf(Error)
    expect(result.current.data).toBeNull()
  })

  it("throws a clear error when used outside its Provider", () => {
    const { useResource } = createResourceContext(async () => null, "Test")
    vi.spyOn(console, "error").mockImplementation(() => {})
    expect(() => renderHook(() => useResource())).toThrow(/must be used inside <TestProvider>/)
  })
})
