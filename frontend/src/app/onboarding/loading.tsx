import { Skeleton } from '@/components/ui/skeleton'

/** Suspense fallback for the onboarding wizard while the route loads. */
export default function Loading() {
  return (
    <div className="min-h-screen bg-brand-paper">
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-10">
        <div className="space-y-3">
          <Skeleton className="h-9 w-64" />
          <Skeleton className="h-5 w-80 max-w-full" />
        </div>
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    </div>
  )
}
