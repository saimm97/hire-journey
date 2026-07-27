import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ProfileOverview } from './ProfileOverview'

const details = {
  identity: {
    first_name: 'Jane',
    last_name: 'Smith',
    phone_number: '+1 555 0100',
    location: 'Berlin, Germany',
    title: 'Backend Engineer',
  },
  accountEmail: 'jane@example.test',
  socialLinks: {
    github_url: 'github.com/jane',
    linkedin_url: 'https://linkedin.com/in/jane',
    portfolio_url: '',
  },
  summary: 'I build reliable distributed systems.',
  technologies: ['Python', 'FastAPI'],
  employment: [
    {
      company_name: 'Acme',
      title: 'Senior Engineer',
      start_date: '2023-02',
      end_date: '',
      description: 'Led the platform team.',
    },
  ],
  education: [
    {
      institution: 'Technical University',
      degree: 'BS',
      field: 'Computer Science',
      start_date: '2017',
      end_date: '2021',
    },
  ],
  certifications: [
    {
      name: 'Cloud Architect',
      issuer: 'Example Cloud',
      issued_at: '2024-03',
      expires_at: '2027-03',
    },
  ],
  projects: [
    {
      project_id: 7,
      name: 'Queue Monitor',
      summary: 'Observability for background jobs.',
      github_url: 'github.com/jane/queue-monitor',
      deployed_url: '',
      technologies: ['React', 'Python'],
    },
  ],
}

const preferences = {
  roles: ['Platform Engineer'],
  locations: ['Berlin, Germany'],
  workModes: ['remote' as const, 'hybrid' as const],
  seniority: 'senior' as const,
  minimumSalary: 120_000,
}

describe('ProfileOverview', () => {
  it('renders saved profile information as a scannable professional record', () => {
    render(<ProfileOverview details={details} preferences={preferences} />)

    expect(screen.getByRole('article', { name: 'Professional profile' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Jane Smith' })).toBeVisible()
    expect(screen.getByText('Senior Engineer')).toBeVisible()
    expect(screen.getByText('Feb 2023 – Present')).toBeVisible()
    expect(screen.getByText('Technical University')).toBeVisible()
    expect(screen.getByText('Queue Monitor')).toBeVisible()
    expect(screen.getAllByText('Python')).toHaveLength(2)
    expect(screen.getByText('$120,000')).toBeVisible()
    expect(
      screen
        .getAllByRole('link', { name: /GitHub/i })
        .some((link) => link.getAttribute('href') === 'https://github.com/jane'),
    ).toBe(true)
  })

  it('names empty sections without inventing profile content', () => {
    render(
      <ProfileOverview
        details={{
          ...details,
          employment: [],
          education: [],
          certifications: [],
          projects: [],
          technologies: [],
        }}
        preferences={{
          roles: [],
          locations: [],
          workModes: [],
          seniority: null,
          minimumSalary: null,
        }}
      />,
    )

    expect(screen.getByText('No work experience has been added.')).toBeVisible()
    expect(screen.getByText('No education has been added.')).toBeVisible()
    expect(screen.getByText('No certifications have been added.')).toBeVisible()
    expect(screen.getByText('No projects have been added.')).toBeVisible()
    expect(screen.getByText('No skills have been added.')).toBeVisible()
    expect(screen.getAllByText('Not specified')).toHaveLength(5)
  })
})
