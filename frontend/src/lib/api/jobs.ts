import { apiRequest } from './client'
import type { JobListResponse } from './types'

export type ListJobsParams = {
  title?: string
  company?: string
  limit?: number
  offset?: number
}

/** Fetch the unranked job catalog using the backend's bounded pagination. */
export function listJobs({
  title,
  company,
  limit = 12,
  offset = 0,
}: ListJobsParams = {}): Promise<JobListResponse> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  const cleanTitle = title?.trim()
  const cleanCompany = company?.trim()
  if (cleanTitle) query.set('title', cleanTitle)
  if (cleanCompany) query.set('company', cleanCompany)

  return apiRequest<JobListResponse>(`/jobs?${query.toString()}`)
}
