import { ExternalLink, Link as LinkIcon, Mail, MapPin, Phone } from 'lucide-react'
import type { ReactNode } from 'react'

import type {
  EditableCertification,
  EditableEducation,
  EditableEmployment,
  EditableProject,
  Identity,
  SocialLinksState,
} from '@/hooks/useOnboardingProfile'
import type { SeniorityLevel, WorkMode } from '@/lib/api/types'

export interface ProfileOverviewDetails {
  identity: Identity
  accountEmail: string
  socialLinks: SocialLinksState
  summary: string
  technologies: string[]
  employment: EditableEmployment[]
  education: EditableEducation[]
  certifications: EditableCertification[]
  projects: EditableProject[]
}

export interface ProfileOverviewPreferences {
  roles: string[]
  locations: string[]
  workModes: WorkMode[]
  seniority: SeniorityLevel | null
  minimumSalary: number | null
}

interface ProfileOverviewProps {
  details: ProfileOverviewDetails
  preferences: ProfileOverviewPreferences
}

const monthFormatter = new Intl.DateTimeFormat('en', {
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

const salaryFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
})

const WORK_MODE_LABELS: Record<WorkMode, string> = {
  remote: 'Remote',
  hybrid: 'Hybrid',
  onsite: 'On-site',
}

function formatMonth(value: string): string {
  if (/^\d{4}$/.test(value)) return value
  if (!/^\d{4}-(?:0[1-9]|1[0-2])/.test(value)) return value
  return monthFormatter.format(new Date(`${value.slice(0, 7)}-01T00:00:00Z`))
}

function dateRange(start: string, end: string, openEnded = false): string {
  if (start && end) return `${formatMonth(start)} – ${formatMonth(end)}`
  if (start) return openEnded ? `${formatMonth(start)} – Present` : formatMonth(start)
  if (end) return `Until ${formatMonth(end)}`
  return 'Dates not provided'
}

function humanize(value: string): string {
  const words = value.replaceAll('_', ' ')
  return words.charAt(0).toUpperCase() + words.slice(1)
}

function externalHref(value: string): string {
  return /^https?:\/\//i.test(value) ? value : `https://${value}`
}

function initials(identity: Identity): string {
  const value = `${identity.first_name.at(0) ?? ''}${identity.last_name.at(0) ?? ''}`
  return value.toUpperCase() || '?'
}

function ProfileSection({
  id,
  title,
  description,
  children,
}: {
  id: string
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section
      aria-labelledby={id}
      className="grid gap-5 px-5 py-7 sm:px-7 lg:grid-cols-[220px_minmax(0,1fr)] lg:gap-10"
    >
      <div>
        <h2 id={id} className="text-xl font-semibold text-brand-ink">
          {title}
        </h2>
        <p className="mt-1 text-sm leading-6 text-brand-muted">{description}</p>
      </div>
      <div className="min-w-0">{children}</div>
    </section>
  )
}

function EmptyValue({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-brand-border bg-brand-paper px-4 py-5 text-sm text-brand-muted">
      {children}
    </div>
  )
}

function Tags({ values }: { values: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {values.map((value) => (
        <span
          key={value}
          className="rounded-full border border-brand-border bg-brand-surface px-3 py-1 text-sm text-brand-ink"
        >
          {value}
        </span>
      ))}
    </div>
  )
}

/** Read-first post-onboarding profile. Editing remains in the hardened onboarding forms. */
export function ProfileOverview({ details, preferences }: ProfileOverviewProps) {
  const fullName = [details.identity.first_name, details.identity.last_name]
    .filter(Boolean)
    .join(' ')
  const socialLinks = [
    { label: 'GitHub', value: details.socialLinks.github_url },
    { label: 'LinkedIn', value: details.socialLinks.linkedin_url },
    { label: 'Portfolio', value: details.socialLinks.portfolio_url },
  ].filter((link) => link.value)

  return (
    <article
      aria-label="Professional profile"
      className="overflow-hidden rounded-xl border border-brand-border bg-white"
    >
      <header className="px-5 py-7 sm:px-7">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start">
          <span className="flex size-14 shrink-0 items-center justify-center rounded-xl bg-brand-primary/10 text-lg font-semibold text-brand-primary">
            {initials(details.identity)}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-semibold text-brand-ink">{fullName || 'Name not added'}</h2>
            <p className="mt-1 text-base text-brand-muted">
              {details.identity.title || 'Professional title not added'}
            </p>

            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-brand-muted">
              {details.identity.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="size-4" aria-hidden="true" />
                  {details.identity.location}
                </span>
              )}
              {details.accountEmail && (
                <a
                  href={`mailto:${details.accountEmail}`}
                  className="inline-flex items-center gap-1.5 hover:text-brand-primary"
                >
                  <Mail className="size-4" aria-hidden="true" />
                  {details.accountEmail}
                </a>
              )}
              {details.identity.phone_number && (
                <a
                  href={`tel:${details.identity.phone_number}`}
                  className="inline-flex items-center gap-1.5 hover:text-brand-primary"
                >
                  <Phone className="size-4" aria-hidden="true" />
                  {details.identity.phone_number}
                </a>
              )}
            </div>

            {socialLinks.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-3 text-sm">
                {socialLinks.map((link) => (
                  <a
                    key={link.label}
                    href={externalHref(link.value)}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-brand-primary hover:underline"
                  >
                    <LinkIcon className="size-3.5" aria-hidden="true" />
                    {link.label}
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 border-t border-brand-border pt-5">
          <h3 className="text-sm font-semibold text-brand-ink">Professional summary</h3>
          <p className="mt-2 whitespace-pre-line text-base leading-7 text-brand-muted">
            {details.summary || 'Add a summary to introduce your experience and career focus.'}
          </p>
        </div>
      </header>

      <div className="divide-y divide-brand-border border-t border-brand-border">
        <ProfileSection
          id="profile-experience"
          title="Work experience"
          description="Roles and professional accomplishments."
        >
          {details.employment.length ? (
            <div className="space-y-3">
              {details.employment.map((item, index) => (
                <div
                  key={`${item.company_name}-${item.title}-${index}`}
                  className="rounded-lg border border-brand-border bg-brand-paper p-4"
                >
                  <h3 className="font-semibold text-brand-ink">{item.title}</h3>
                  <p className="mt-0.5 text-sm font-medium text-brand-primary">
                    {item.company_name}
                  </p>
                  <p className="mt-1 font-mono text-xs text-brand-muted">
                    {dateRange(item.start_date, item.end_date, true)}
                  </p>
                  {item.description && (
                    <p className="mt-3 whitespace-pre-line text-sm leading-6 text-brand-ink">
                      {item.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyValue>No work experience has been added.</EmptyValue>
          )}
        </ProfileSection>

        <ProfileSection
          id="profile-education"
          title="Education"
          description="Schools, degrees, and areas of study."
        >
          {details.education.length ? (
            <div className="space-y-3">
              {details.education.map((item, index) => (
                <div
                  key={`${item.institution}-${item.degree}-${index}`}
                  className="rounded-lg border border-brand-border bg-brand-paper p-4"
                >
                  <h3 className="font-semibold text-brand-ink">{item.institution}</h3>
                  {(item.degree || item.field) && (
                    <p className="mt-1 text-sm text-brand-ink">
                      {[item.degree, item.field].filter(Boolean).join(' · ')}
                    </p>
                  )}
                  <p className="mt-1 font-mono text-xs text-brand-muted">
                    {dateRange(item.start_date, item.end_date)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyValue>No education has been added.</EmptyValue>
          )}
        </ProfileSection>

        <ProfileSection
          id="profile-certifications"
          title="Certifications"
          description="Professional credentials and qualifications."
        >
          {details.certifications.length ? (
            <div className="space-y-3">
              {details.certifications.map((item, index) => (
                <div
                  key={`${item.name}-${item.issuer}-${index}`}
                  className="rounded-lg border border-brand-border bg-brand-paper p-4"
                >
                  <h3 className="font-semibold text-brand-ink">{item.name}</h3>
                  {item.issuer && <p className="mt-1 text-sm text-brand-ink">{item.issuer}</p>}
                  <p className="mt-1 font-mono text-xs text-brand-muted">
                    {item.issued_at ? `Issued ${formatMonth(item.issued_at)}` : 'Issue date not provided'}
                    {item.expires_at ? ` · Expires ${formatMonth(item.expires_at)}` : ''}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyValue>No certifications have been added.</EmptyValue>
          )}
        </ProfileSection>

        <ProfileSection
          id="profile-projects"
          title="Projects"
          description="Selected work and the technology behind it."
        >
          {details.projects.length ? (
            <div className="space-y-3">
              {details.projects.map((item, index) => (
                <div
                  key={item.project_id ?? `${item.name}-${index}`}
                  className="rounded-lg border border-brand-border bg-brand-paper p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="font-semibold text-brand-ink">{item.name}</h3>
                    <div className="flex gap-3 text-sm">
                      {item.github_url && (
                        <a
                          href={externalHref(item.github_url)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-brand-primary hover:underline"
                        >
                          GitHub <ExternalLink className="size-3.5" aria-hidden="true" />
                        </a>
                      )}
                      {item.deployed_url && (
                        <a
                          href={externalHref(item.deployed_url)}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-brand-primary hover:underline"
                        >
                          Live <ExternalLink className="size-3.5" aria-hidden="true" />
                        </a>
                      )}
                    </div>
                  </div>
                  {item.summary && (
                    <p className="mt-2 whitespace-pre-line text-sm leading-6 text-brand-ink">
                      {item.summary}
                    </p>
                  )}
                  {item.technologies.length > 0 && (
                    <div className="mt-3">
                      <Tags values={item.technologies} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyValue>No projects have been added.</EmptyValue>
          )}
        </ProfileSection>

        <ProfileSection
          id="profile-skills"
          title="Skills"
          description="Technologies represented in your professional profile."
        >
          {details.technologies.length ? (
            <Tags values={details.technologies} />
          ) : (
            <EmptyValue>No skills have been added.</EmptyValue>
          )}
        </ProfileSection>

        <ProfileSection
          id="profile-preferences"
          title="Job preferences"
          description="The roles, locations, and terms guiding your matches."
        >
          <dl className="grid gap-5 sm:grid-cols-2">
            <div>
              <dt className="text-sm font-semibold text-brand-ink">Desired roles</dt>
              <dd className="mt-2">
                {preferences.roles.length ? (
                  <Tags values={preferences.roles} />
                ) : (
                  <span className="text-sm text-brand-muted">Not specified</span>
                )}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-brand-ink">Desired locations</dt>
              <dd className="mt-2 text-sm leading-6 text-brand-muted">
                {preferences.locations.join(' · ') || 'Not specified'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-brand-ink">Work modes</dt>
              <dd className="mt-2 text-sm text-brand-muted">
                {preferences.workModes.map((mode) => WORK_MODE_LABELS[mode]).join(' · ') ||
                  'Not specified'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-brand-ink">Seniority</dt>
              <dd className="mt-2 text-sm text-brand-muted">
                {preferences.seniority ? humanize(preferences.seniority) : 'Not specified'}
              </dd>
            </div>
            <div>
              <dt className="text-sm font-semibold text-brand-ink">Minimum salary</dt>
              <dd className="mt-2 font-mono text-sm text-brand-muted">
                {preferences.minimumSalary == null
                  ? 'Not specified'
                  : salaryFormatter.format(preferences.minimumSalary)}
              </dd>
            </div>
          </dl>
        </ProfileSection>
      </div>
    </article>
  )
}
