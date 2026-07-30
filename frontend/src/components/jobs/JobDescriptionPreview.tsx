"use client"

import { cn } from "@/lib/utils"

function SanitizedHtmlDescription({ html }: { html: string }) {
  return (
    <div
      className={cn(
        "mt-5 overflow-x-auto whitespace-pre-line text-[15px] leading-7 text-brand-ink/90",
        "[&_a]:font-medium [&_a]:text-brand-primary [&_a]:underline [&_a]:underline-offset-2",
        "[&_blockquote]:my-5 [&_blockquote]:border-l-2 [&_blockquote]:border-brand-border [&_blockquote]:pl-4 [&_blockquote]:text-brand-muted",
        "[&_code]:rounded [&_code]:bg-brand-surface [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[13px]",
        "[&_dd]:ml-4 [&_dl]:my-5 [&_dt]:font-semibold",
        "[&_h1]:mb-3 [&_h1]:mt-8 [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:text-brand-ink",
        "[&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-brand-ink",
        "[&_h3]:mb-2 [&_h3]:mt-7 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-brand-ink",
        "[&_h4]:mb-2 [&_h4]:mt-6 [&_h4]:font-semibold [&_h4]:text-brand-ink",
        "[&_h5]:mb-2 [&_h5]:mt-5 [&_h5]:font-semibold [&_h5]:text-brand-ink",
        "[&_h6]:mb-2 [&_h6]:mt-5 [&_h6]:font-semibold [&_h6]:text-brand-ink",
        "[&_hr]:my-7 [&_hr]:border-brand-border",
        "[&_li]:my-1.5 [&_ol]:my-4 [&_ol]:list-decimal [&_ol]:pl-6",
        "[&_p]:my-4 [&_pre]:my-5 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-brand-surface [&_pre]:p-4",
        "[&_strong]:font-semibold [&_table]:my-5 [&_table]:w-full [&_table]:border-collapse",
        "[&_td]:border [&_td]:border-brand-border [&_td]:p-2 [&_th]:border [&_th]:border-brand-border [&_th]:bg-brand-surface [&_th]:p-2 [&_th]:text-left",
        "[&_ul]:my-4 [&_ul]:list-disc [&_ul]:pl-6",
        "[&>*:first-child]:mt-0 [&>*:last-child]:mb-0",
      )}
      data-testid="html-job-description"
      // The backend emits this field only after strict tag/attribute/URL sanitization.
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export function JobDescriptionPreview({
  description,
}: {
  description: string | null
}) {
  const cleanDescription = description?.trim() ?? ""

  return (
    <section className="mt-8 border-t border-brand-border pt-7" aria-labelledby="job-description-heading">
      <h3 id="job-description-heading" className="text-lg font-semibold text-brand-ink">
        Job description
      </h3>

      {cleanDescription ? (
        <SanitizedHtmlDescription html={cleanDescription} />
      ) : (
        <p className="mt-4 text-sm text-brand-muted">
          A description is not available in the catalog. Open the original posting for full details.
        </p>
      )}
    </section>
  )
}
