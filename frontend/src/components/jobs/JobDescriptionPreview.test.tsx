import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { JobDescriptionPreview } from './JobDescriptionPreview'

describe('JobDescriptionPreview', () => {
  it('renders the sanitized semantic HTML supplied by the backend', () => {
    render(
      <JobDescriptionPreview
        description={
          '<h2>Responsibilities</h2><p>Build APIs</p><h2>Requirements</h2><ul><li>Five years of experience</li><li>Python</li></ul>'
        }
      />,
    )

    const htmlDescription = screen.getByTestId('html-job-description')
    expect(
      within(htmlDescription).getByRole('heading', { name: 'Responsibilities' }),
    ).toBeInTheDocument()
    expect(
      within(htmlDescription).getByRole('heading', { name: 'Requirements' }),
    ).toBeInTheDocument()
    expect(within(htmlDescription).getByRole('list')).toBeInTheDocument()
    expect(within(htmlDescription).getAllByRole('listitem')).toHaveLength(2)
  })

  it('renders legacy plain-text descriptions without requiring a second field', () => {
    render(<JobDescriptionPreview description="An older flattened job description." />)

    expect(screen.getByTestId('html-job-description')).toHaveTextContent(
      'An older flattened job description.',
    )
  })

  it('keeps the missing-description fallback', () => {
    render(<JobDescriptionPreview description={null} />)

    expect(screen.getByText(/description is not available/i)).toBeInTheDocument()
  })
})
