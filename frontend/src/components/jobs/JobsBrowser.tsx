"use client"

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react"
import {
  AlertCircle,
  ArrowLeft,
  ArrowUpRight,
  Banknote,
  BriefcaseBusiness,
  Building2,
  CalendarDays,
  MapPin,
  Search,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { JobDescriptionPreview } from "@/components/jobs/JobDescriptionPreview"
import { ApiError } from "@/lib/api/client"
import { listJobs } from "@/lib/api/jobs"
import type { Job } from "@/lib/api/types"
import { cn } from "@/lib/utils"

const PAGE_SIZE = 12
const MOBILE_QUERY = "(max-width: 1023px)"
const integerFormatter = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 })
const compactFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})
const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
})

type Filters = {
  title: string
  company: string
}

type LoadError = {
  message: string
  requestId?: string
}

function hasSalary(job: Job): boolean {
  return job.salary_min !== null || job.salary_max !== null
}

function formatSalary(job: Job): string {
  const minimum = job.salary_min
  const maximum = job.salary_max

  if (minimum !== null && maximum !== null) {
    return `${compactFormatter.format(minimum)}–${compactFormatter.format(maximum)} yearly`
  }
  if (minimum !== null) return `From ${compactFormatter.format(minimum)} yearly`
  if (maximum !== null) return `Up to ${compactFormatter.format(maximum)} yearly`
  return "Salary not listed"
}

function formatDeadline(value: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : dateFormatter.format(date)
}

function ScoreBubble() {
  return (
    <span
      className="flex size-11 shrink-0 items-center justify-center rounded-full border border-brand-border bg-brand-surface text-lg font-semibold text-brand-muted"
      aria-label="Match score unavailable"
      title="A profile match score will appear here once ranking is enabled."
    >
      —
    </span>
  )
}

function JobListItem({
  job,
  selected,
  onSelect,
}: {
  job: Job
  selected: boolean
  onSelect: (trigger: HTMLButtonElement) => void
}) {
  return (
    <button
      type="button"
      className={cn(
        "w-full border-l-4 border-b border-brand-border px-4 py-4 text-left outline-none transition-colors focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-primary",
        selected
          ? "border-l-brand-primary bg-blue-50/80"
          : "border-l-transparent bg-white hover:bg-brand-paper",
      )}
      onClick={(event) => onSelect(event.currentTarget)}
      aria-pressed={selected}
      aria-controls="selected-job-details"
    >
      <span className="flex gap-3">
        <ScoreBubble />
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-semibold leading-5 text-brand-ink">
            {job.title}
          </span>
          <span className="mt-1 block truncate text-sm font-medium text-brand-primary">
            {job.company_name}
          </span>
          <span className="mt-2 flex min-w-0 items-center gap-1.5 text-xs text-brand-muted">
            <MapPin className="size-3.5 shrink-0" aria-hidden="true" />
            <span className="truncate">{job.location?.trim() || "Location not specified"}</span>
          </span>
          <span className="mt-3 block truncate text-xs text-brand-muted">
            {formatSalary(job)}
          </span>
        </span>
      </span>
    </button>
  )
}

function JobDetail({ job, onBack }: { job: Job; onBack: () => void }) {
  const deadline = formatDeadline(job.deadline)

  return (
    <article
      id="selected-job-details"
      className="min-h-full bg-white"
      aria-labelledby={`selected-job-title-${job.id}`}
    >
      <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-brand-border bg-white px-4 py-3 lg:hidden">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" /> Back to jobs
        </Button>
      </div>

      <div className="p-5 sm:p-7 lg:p-8">
        <div className="flex items-start gap-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-xl border border-brand-border bg-brand-surface text-brand-muted">
            <Building2 className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2
              id={`selected-job-title-${job.id}`}
              className="text-2xl font-semibold leading-8 tracking-tight text-brand-ink"
            >
              {job.title}
            </h2>
            <p className="mt-1 text-base font-medium text-brand-primary">{job.company_name}</p>
            <p className="mt-1 flex items-center gap-1.5 text-sm text-brand-muted">
              <MapPin className="size-4 shrink-0" aria-hidden="true" />
              {job.location?.trim() || "Location not specified"}
            </p>
          </div>
        </div>

        <Button asChild size="lg" className="mt-6 w-full sm:w-auto">
          <a href={job.url} target="_blank" rel="noreferrer">
            View original posting <ArrowUpRight className="size-4" aria-hidden="true" />
          </a>
        </Button>

        <dl className="mt-7 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-brand-border bg-brand-paper p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-brand-muted">
              <Banknote className="size-4" aria-hidden="true" /> Salary
            </dt>
            <dd className="mt-2 text-sm font-semibold text-brand-ink">
              {formatSalary(job)}
              {hasSalary(job) && (
                <span className="mt-1 block text-xs font-normal text-brand-muted">
                  Verify currency in the posting.
                </span>
              )}
            </dd>
          </div>
          <div className="rounded-lg border border-brand-border bg-brand-paper p-4">
            <dt className="flex items-center gap-2 text-xs font-medium text-brand-muted">
              <CalendarDays className="size-4" aria-hidden="true" /> Application deadline
            </dt>
            <dd className="mt-2 text-sm font-semibold text-brand-ink">
              {deadline ? <time dateTime={job.deadline ?? undefined}>{deadline}</time> : "Not listed"}
            </dd>
          </div>
        </dl>

        <JobDescriptionPreview key={job.id} description={job.description} />
      </div>
    </article>
  )
}

function WorkspaceSkeleton() {
  return (
    <div
      className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(320px,390px)_minmax(0,1fr)]"
      role="status"
      aria-label="Loading jobs"
    >
      <div className="overflow-hidden rounded-xl border border-brand-border bg-white">
        <div className="border-b border-brand-border px-4 py-4">
          <Skeleton className="h-5 w-32" />
        </div>
        {Array.from({ length: 6 }, (_, index) => (
          <div key={index} className="flex gap-3 border-b border-brand-border p-4 last:border-b-0">
            <Skeleton className="size-11 shrink-0 rounded-full" />
            <div className="flex-1 space-y-2.5">
              <Skeleton className="h-4 w-4/5" />
              <Skeleton className="h-3.5 w-2/5" />
              <Skeleton className="h-3.5 w-3/5" />
            </div>
          </div>
        ))}
      </div>
      <div className="hidden rounded-xl border border-brand-border bg-white p-8 lg:block">
        <div className="flex gap-4">
          <Skeleton className="size-12 shrink-0" />
          <div className="flex-1 space-y-3">
            <Skeleton className="h-7 w-3/4" />
            <Skeleton className="h-4 w-2/5" />
          </div>
        </div>
        <Skeleton className="mt-7 h-11 w-48" />
        <div className="mt-8 space-y-3">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </div>
      <span className="sr-only">Loading jobs…</span>
    </div>
  )
}

export function JobsBrowser() {
  const [titleInput, setTitleInput] = useState("")
  const [companyInput, setCompanyInput] = useState("")
  const [filters, setFilters] = useState<Filters>({ title: "", company: "" })
  const [offset, setOffset] = useState(0)
  const [reloadNonce, setReloadNonce] = useState(0)
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null)
  const [mobileDetailOpen, setMobileDetailOpen] = useState(false)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<LoadError | null>(null)
  const detailPanelRef = useRef<HTMLElement>(null)
  const mobileTriggerRef = useRef<HTMLButtonElement | null>(null)

  const closeMobileDetail = useCallback(() => {
    setMobileDetailOpen(false)
    window.requestAnimationFrame(() => mobileTriggerRef.current?.focus())
  }, [])

  useEffect(() => {
    let active = true

    void listJobs({
      title: filters.title,
      company: filters.company,
      limit: PAGE_SIZE,
      offset,
    })
      .then((response) => {
        if (!active) return
        setJobs(response.results)
        setSelectedJobId(response.results[0]?.id ?? null)
        setMobileDetailOpen(false)
        setTotal(response.total)
        setLoading(false)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError({
          message:
            reason instanceof ApiError
              ? reason.message
              : "We couldn't load jobs. Please try again.",
          requestId: reason instanceof ApiError ? reason.requestId : undefined,
        })
        setLoading(false)
      })

    return () => {
      active = false
    }
  }, [filters, offset, reloadNonce])

  useEffect(() => {
    if (!mobileDetailOpen) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeMobileDetail()
    }
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    detailPanelRef.current?.focus()
    window.addEventListener("keydown", closeOnEscape)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener("keydown", closeOnEscape)
    }
  }, [closeMobileDetail, mobileDetailOpen])

  const selectedJob = jobs.find((job) => job.id === selectedJobId) ?? jobs[0] ?? null
  const hasFilters = Boolean(filters.title || filters.company)
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))
  const rangeStart = total === 0 ? 0 : offset + 1
  const rangeEnd = Math.min(offset + jobs.length, total)

  function prepareForLoad() {
    setLoading(true)
    setError(null)
    setMobileDetailOpen(false)
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const next = { title: titleInput.trim(), company: companyInput.trim() }
    const unchanged = next.title === filters.title && next.company === filters.company
    prepareForLoad()
    setOffset(0)
    setFilters(next)
    if (unchanged && offset === 0) setReloadNonce((value) => value + 1)
  }

  function clearFilters() {
    prepareForLoad()
    setTitleInput("")
    setCompanyInput("")
    setOffset(0)
    if (!hasFilters) setReloadNonce((value) => value + 1)
    setFilters({ title: "", company: "" })
  }

  function selectJob(jobId: number, trigger: HTMLButtonElement) {
    setSelectedJobId(jobId)
    if (window.matchMedia?.(MOBILE_QUERY).matches) {
      mobileTriggerRef.current = trigger
      setMobileDetailOpen(true)
    }
  }

  return (
    <div className="mx-auto max-w-7xl">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-[32px] font-semibold leading-10 tracking-tight text-brand-ink">Jobs</h1>
          <p className="max-w-2xl text-brand-muted">
            Explore roles collected from supported company career boards.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-brand-muted" aria-live="polite">
          <BriefcaseBusiness className="size-4" aria-hidden="true" />
          {loading
            ? "Loading catalog…"
            : `${integerFormatter.format(total)} ${total === 1 ? "role" : "roles"}`}
        </div>
      </header>

      <form
        className="mt-6 grid gap-4 rounded-xl border border-brand-border bg-white p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end sm:p-5"
        onSubmit={submitSearch}
        role="search"
      >
        <label className="space-y-1.5 text-sm font-medium text-brand-ink">
          Job title
          <span className="relative block">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-brand-muted"
              aria-hidden="true"
            />
            <Input
              value={titleInput}
              onChange={(event) => setTitleInput(event.target.value)}
              placeholder="e.g. Software Engineer"
              className="h-11 pl-9"
            />
          </span>
        </label>
        <label className="space-y-1.5 text-sm font-medium text-brand-ink">
          Company
          <Input
            value={companyInput}
            onChange={(event) => setCompanyInput(event.target.value)}
            placeholder="e.g. Stability AI"
            className="h-11"
          />
        </label>
        <Button type="submit" size="lg" disabled={loading}>
          Search jobs
        </Button>
      </form>

      <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
        <span className="font-semibold">Catalog view.</span>{" "}
        All available roles are shown. Match scores will appear when personalized ranking is enabled.
      </div>

      {loading && <WorkspaceSkeleton />}

      {!loading && error && (
        <div
          className="mt-6 rounded-xl border border-red-200 bg-white px-6 py-12 text-center"
          role="alert"
        >
          <AlertCircle className="mx-auto size-7 text-destructive" aria-hidden="true" />
          <h2 className="mt-3 text-lg font-semibold text-brand-ink">Jobs couldn&apos;t load</h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-brand-muted">{error.message}</p>
          {error.requestId && (
            <p className="mt-2 font-mono text-xs text-brand-muted">
              Request reference: {error.requestId}
            </p>
          )}
          <Button
            className="mt-5"
            onClick={() => {
              prepareForLoad()
              setReloadNonce((value) => value + 1)
            }}
          >
            Try again
          </Button>
        </div>
      )}

      {!loading && !error && jobs.length === 0 && (
        <div className="mt-6 rounded-xl border border-dashed border-brand-border bg-white px-6 py-12 text-center">
          <BriefcaseBusiness className="mx-auto size-8 text-brand-muted" aria-hidden="true" />
          <h2 className="mt-3 text-lg font-semibold text-brand-ink">
            {hasFilters ? "No roles match those filters" : "No jobs are available yet"}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-brand-muted">
            {hasFilters
              ? "Try a broader title or company name."
              : "Roles will appear here after the ingestion pipeline stores them."}
          </p>
          {hasFilters && (
            <Button className="mt-5" variant="outline" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      )}

      {!loading && !error && jobs.length > 0 && selectedJob && (
        <div className="mt-6 grid items-start gap-5 lg:grid-cols-[minmax(320px,390px)_minmax(0,1fr)]">
          <section
            className="overflow-hidden rounded-xl border border-brand-border bg-white lg:sticky lg:top-6 lg:flex lg:max-h-[calc(100vh-3rem)] lg:flex-col"
            aria-labelledby="jobs-results-heading"
          >
            <div className="flex items-center justify-between gap-3 border-b border-brand-border px-4 py-4">
              <div>
                <h2 id="jobs-results-heading" className="font-semibold text-brand-ink">
                  Available roles
                </h2>
                <p className="mt-0.5 text-xs text-brand-muted">
                  {integerFormatter.format(rangeStart)}–{integerFormatter.format(rangeEnd)} of{" "}
                  {integerFormatter.format(total)}
                </p>
              </div>
              <span className="text-xs text-brand-muted">Select a role</span>
            </div>

            <ul className="lg:min-h-0 lg:flex-1 lg:overflow-y-auto">
              {jobs.map((job) => (
                <li key={job.id}>
                  <JobListItem
                    job={job}
                    selected={job.id === selectedJob.id}
                    onSelect={(trigger) => selectJob(job.id, trigger)}
                  />
                </li>
              ))}
            </ul>

            {total > PAGE_SIZE && (
              <nav
                className="flex items-center justify-between gap-2 border-t border-brand-border bg-white px-3 py-3"
                aria-label="Jobs pagination"
              >
                <Button
                  size="sm"
                  variant="outline"
                  disabled={offset === 0}
                  onClick={() => {
                    prepareForLoad()
                    setOffset((value) => Math.max(0, value - PAGE_SIZE))
                  }}
                >
                  Previous
                </Button>
                <span className="text-xs text-brand-muted">
                  {integerFormatter.format(page)} / {integerFormatter.format(pageCount)}
                </span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => {
                    prepareForLoad()
                    setOffset((value) => value + PAGE_SIZE)
                  }}
                >
                  Next
                </Button>
              </nav>
            )}
          </section>

          <aside
            ref={detailPanelRef}
            className={cn(
              "bg-white lg:sticky lg:inset-auto lg:top-6 lg:block lg:max-h-[calc(100vh-3rem)] lg:overflow-y-auto lg:rounded-xl lg:border lg:border-brand-border",
              mobileDetailOpen
                ? "fixed inset-0 z-50 block overflow-y-auto"
                : "hidden",
            )}
            role={mobileDetailOpen ? "dialog" : undefined}
            aria-modal={mobileDetailOpen ? "true" : undefined}
            aria-label="Selected job details"
            tabIndex={-1}
          >
            <JobDetail job={selectedJob} onBack={closeMobileDetail} />
          </aside>
        </div>
      )}
    </div>
  )
}
