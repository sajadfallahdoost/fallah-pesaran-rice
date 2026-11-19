import { notFound } from "next/navigation";

import { PageIntro, RichText } from "@/components/catalog";
import { InfoIcon } from "@/components/icons";
import { getPage, NotFoundError } from "@/lib/api-server";
import { jalaliDate } from "@/lib/format";

export async function loadPage(slug: string) {
  try {
    return await getPage(slug);
  } catch (error) {
    if (error instanceof NotFoundError) notFound();
    throw error;
  }
}

export async function ContentPageView({ slug, crumbs }: { slug: string; crumbs?: { href?: string; label: string }[] }) {
  const page = await loadPage(slug);
  return (
    <>
      <PageIntro title={page.title} description={page.summary} crumbs={[...(crumbs ?? []), { label: page.title }]} />
      <div className="container-page max-w-3xl py-10">
        {page.requires_owner_review && (
          <p className="mb-8 flex items-start gap-2 rounded-xl border border-gold-500/40 bg-gold-100/60 px-4 py-3 text-sm leading-7 text-gold-700">
            <InfoIcon size={18} className="mt-1 shrink-0" />
            این متن پیش‌نویس است و پس از تأیید مالک فروشگاه نهایی می‌شود.
          </p>
        )}
        <RichText text={page.body} />
        <p className="mt-10 text-xs text-ink-muted">آخرین به‌روزرسانی: {jalaliDate(page.updated_at)}</p>
      </div>
    </>
  );
}

export function ContentSkeleton() {
  return (
    <div className="container-page max-w-3xl space-y-4 py-12" aria-hidden="true">
      <div className="skeleton h-9 w-1/2" />
      <div className="skeleton h-4 w-full" />
      <div className="skeleton h-4 w-11/12" />
      <div className="skeleton h-4 w-4/5" />
    </div>
  );
}
