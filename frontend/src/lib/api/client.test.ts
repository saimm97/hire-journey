import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiRequest } from './client'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function capturedApiError(body: unknown): Promise<ApiError> {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(JSON.stringify(body), {
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: { 'Content-Type': 'application/json' },
      }),
    ),
  )

  try {
    await apiRequest('/profile', { method: 'PATCH', body: { details: {} } })
    throw new Error('Expected apiRequest to reject')
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError)
    return error as ApiError
  }
}

describe('apiRequest error normalization', () => {
  it('preserves the new error envelope and its field paths', async () => {
    const error = await capturedApiError({
      error: {
        code: 'validation_error',
        message: 'Some details need fixing.',
        fields: [
          {
            path: ['education', 0, 'start_date'],
            message: 'Use YYYY or YYYY-MM.',
          },
        ],
        request_id: 'req-123',
      },
    })

    expect(error.message).toBe('Some details need fixing.')
    expect(error.message).not.toContain('[object Object]')
    expect(error.code).toBe('validation_error')
    expect(error.requestId).toBe('req-123')
    expect(error.fieldError(['education', 0, 'start_date'])).toBe('Use YYYY or YYYY-MM.')
  })

  it('converts the legacy FastAPI validation array without stringifying objects', async () => {
    const error = await capturedApiError({
      detail: [
        {
          loc: ['body', 'education', 0, 'start_date'],
          msg: 'Value error, must be in YYYY or YYYY-MM format',
          type: 'value_error',
        },
      ],
    })

    expect(error.message).toBe('Some details need fixing.')
    expect(error.message).not.toContain('[object Object]')
    expect(error.fields).toEqual([
      {
        path: ['education', 0, 'start_date'],
        message: 'must be in YYYY or YYYY-MM format',
      },
    ])
  })

  it('times out when fetch never resolves', async () => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        const signal = init?.signal
        return new Promise<Response>((_resolve, reject) => {
          signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
        })
      }),
    )

    const request = apiRequest('/profile', { timeoutMs: 25 })
    const rejection = expect(request).rejects.toMatchObject({ code: 'timeout', status: 0 })
    await vi.advanceTimersByTimeAsync(25)
    await rejection
  })

  it.each([
    { name: 'successful', response: { ok: true, status: 200, statusText: 'OK' } },
    {
      name: 'error',
      response: { ok: false, status: 422, statusText: 'Unprocessable Entity' },
    },
  ])('keeps the timeout active while a $name response body stalls', async ({ response }) => {
    vi.useFakeTimers()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        const signal = init?.signal
        return Promise.resolve({
          ...response,
          json: () =>
            new Promise<never>((_resolve, reject) => {
              signal?.addEventListener('abort', () =>
                reject(new DOMException('Aborted', 'AbortError')),
              )
            }),
        } as unknown as Response)
      }),
    )

    const request = apiRequest('/profile', { timeoutMs: 25 })
    const rejection = expect(request).rejects.toMatchObject({ code: 'timeout', status: 0 })
    await vi.advanceTimersByTimeAsync(25)
    await rejection
  })

  it('classifies a genuine fetch rejection as a network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('connection lost')))

    await expect(apiRequest('/profile')).rejects.toMatchObject({
      code: 'network_error',
      status: 0,
    })
  })

  it('classifies malformed successful JSON as an invalid response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response('not-json', {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )

    await expect(apiRequest('/profile')).rejects.toMatchObject({
      code: 'invalid_response',
      status: 200,
      message: 'The server returned an unexpected response. Please try again.',
    })
  })
})
