import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/lib/api/client'
import type { Job, JobListResponse } from '@/lib/api/types'

vi.mock('@/lib/api/jobs', () => ({
  listJobs: vi.fn(),
}))

import { listJobs } from '@/lib/api/jobs'
import { JobsBrowser } from './JobsBrowser'

const listJobsMock = vi.mocked(listJobs)

const job: Job = {
  id: 42,
  title: 'Senior Platform Engineer',
  company_name: 'Stability AI',
  location: 'London, UK',
  url: 'https://jobs.example.com/platform-engineer',
  description: '<p>Build reliable infrastructure for machine learning products.</p>',
  salary_min: 120_000,
  salary_max: 180_000,
  deadline: '2026-08-31T00:00:00Z',
}

const secondJob: Job = {
  id: 84,
  title: 'Machine Learning Engineer',
  company_name: 'Runway',
  location: 'New York, NY',
  url: 'https://jobs.example.com/machine-learning-engineer',
  description: '<p>Ship models and tooling for generative media products.</p>',
  salary_min: null,
  salary_max: null,
  deadline: null,
}

const catalog: JobListResponse = { total: 1, results: [job] }

describe('JobsBrowser', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders a selected result and its full detail without inventing a score', async () => {
    listJobsMock.mockResolvedValue(catalog)
    render(<JobsBrowser />)

    expect(screen.getByRole('status', { name: 'Loading jobs' })).toBeInTheDocument()
    const detail = await screen.findByRole('complementary', { name: 'Selected job details' })

    expect(
      within(detail).getByRole('heading', { name: 'Senior Platform Engineer' }),
    ).toBeInTheDocument()
    expect(within(detail).getByText('Stability AI')).toBeInTheDocument()
    expect(within(detail).getByText('120K–180K yearly')).toBeInTheDocument()
    expect(within(detail).getByText('Aug 31, 2026')).toBeInTheDocument()
    expect(
      within(detail).getByText('Build reliable infrastructure for machine learning products.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Match score unavailable')).toHaveTextContent('—')
    expect(screen.getByText(/Match scores will appear/i)).toBeInTheDocument()

    const selectedResult = screen.getByRole('button', { name: /Senior Platform Engineer/ })
    expect(selectedResult).toHaveAttribute('aria-pressed', 'true')

    const roleLink = within(detail).getByRole('link', { name: /View original posting/ })
    expect(roleLink).toHaveAttribute('href', job.url)
    expect(roleLink).toHaveAttribute('target', '_blank')
    expect(roleLink).toHaveAttribute('rel', 'noreferrer')
    expect(listJobsMock).toHaveBeenCalledWith({
      title: '',
      company: '',
      limit: 12,
      offset: 0,
    })
  })

  it('switches the detail pane when another result is selected', async () => {
    const user = userEvent.setup()
    listJobsMock.mockResolvedValue({ total: 2, results: [job, secondJob] })
    render(<JobsBrowser />)

    const detail = await screen.findByRole('complementary', { name: 'Selected job details' })
    const firstResult = screen.getByRole('button', { name: /Senior Platform Engineer/ })
    const secondResult = screen.getByRole('button', { name: /Machine Learning Engineer/ })
    expect(firstResult).toHaveAttribute('aria-pressed', 'true')

    await user.click(secondResult)

    expect(secondResult).toHaveAttribute('aria-pressed', 'true')
    expect(firstResult).toHaveAttribute('aria-pressed', 'false')
    expect(
      within(detail).getByRole('heading', { name: 'Machine Learning Engineer' }),
    ).toBeInTheDocument()
    expect(within(detail).getByText('Salary not listed')).toBeInTheDocument()
    expect(within(detail).getByText('Not listed')).toBeInTheDocument()
  })

  it('opens a focused mobile detail view and returns focus to the selected result', async () => {
    const user = userEvent.setup()
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockReturnValue({
        matches: true,
        media: '(max-width: 1023px)',
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }),
    )
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0)
      return 1
    })
    listJobsMock.mockResolvedValue({ total: 2, results: [job, secondJob] })
    render(<JobsBrowser />)
    await screen.findByRole('complementary', { name: 'Selected job details' })

    const result = screen.getByRole('button', { name: /Machine Learning Engineer/ })
    await user.click(result)

    const dialog = screen.getByRole('dialog', { name: 'Selected job details' })
    expect(dialog).toHaveFocus()
    expect(document.body.style.overflow).toBe('hidden')

    await user.click(within(dialog).getByRole('button', { name: 'Back to jobs' }))

    expect(screen.queryByRole('dialog', { name: 'Selected job details' })).not.toBeInTheDocument()
    expect(document.body.style.overflow).toBe('')
    expect(result).toHaveFocus()
  })

  it('applies title and company search through the paginated API', async () => {
    const user = userEvent.setup()
    listJobsMock.mockResolvedValueOnce(catalog).mockResolvedValueOnce(catalog)
    render(<JobsBrowser />)
    await screen.findByRole('complementary', { name: 'Selected job details' })

    await user.type(screen.getByRole('textbox', { name: 'Job title' }), '  Platform  ')
    await user.type(screen.getByRole('textbox', { name: 'Company' }), ' Stability AI ')
    await user.click(screen.getByRole('button', { name: 'Search jobs' }))

    await waitFor(() =>
      expect(listJobsMock).toHaveBeenLastCalledWith({
        title: 'Platform',
        company: 'Stability AI',
        limit: 12,
        offset: 0,
      }),
    )
  })

  it('requests each page from FastAPI instead of paginating a local collection', async () => {
    const user = userEvent.setup()
    listJobsMock.mockResolvedValue({ total: 25, results: [job] })
    render(<JobsBrowser />)
    const pagination = await screen.findByRole('navigation', { name: 'Jobs pagination' })
    expect(within(pagination).getByText('1 / 3')).toBeInTheDocument()

    await user.click(within(pagination).getByRole('button', { name: 'Next' }))

    await waitFor(() =>
      expect(listJobsMock).toHaveBeenLastCalledWith({
        title: '',
        company: '',
        limit: 12,
        offset: 12,
      }),
    )
    expect(await screen.findByText('2 / 3')).toBeInTheDocument()
  })

  it('shows a safe recoverable error with its request reference', async () => {
    const user = userEvent.setup()
    listJobsMock
      .mockRejectedValueOnce(
        new ApiError(500, {
          message: 'Jobs are temporarily unavailable.',
          requestId: 'req-jobs-123',
        }),
      )
      .mockResolvedValueOnce({ total: 0, results: [] })
    render(<JobsBrowser />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Jobs are temporarily unavailable.')
    expect(alert).toHaveTextContent('Request reference: req-jobs-123')

    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(
      await screen.findByRole('heading', { name: 'No jobs are available yet' }),
    ).toBeInTheDocument()
    expect(listJobsMock).toHaveBeenCalledTimes(2)
  })
})
