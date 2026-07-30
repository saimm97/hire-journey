import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('./client', () => ({
  apiRequest: vi.fn(),
}))

import { apiRequest } from './client'
import { listJobs } from './jobs'

const apiRequestMock = vi.mocked(apiRequest)

describe('listJobs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiRequestMock.mockResolvedValue({ total: 0, results: [] })
  })

  it('sends bounded pagination and trimmed optional filters', async () => {
    await listJobs({
      title: '  Software Engineer  ',
      company: '  Stability AI ',
      limit: 12,
      offset: 24,
    })

    expect(apiRequestMock).toHaveBeenCalledWith(
      '/jobs?limit=12&offset=24&title=Software+Engineer&company=Stability+AI',
    )
  })

  it('omits empty filters', async () => {
    await listJobs({ title: '  ', company: '' })

    expect(apiRequestMock).toHaveBeenCalledWith('/jobs?limit=12&offset=0')
  })
})
