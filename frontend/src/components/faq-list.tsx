import { PlusIcon } from "@/components/icons";
import type { Faq } from "@/lib/types";

export function FaqList({ faqs }: { faqs: Faq[] }) {
  return (
    <div className="divide-y divide-line overflow-hidden rounded-[var(--radius-card)] border border-line bg-white">
      {faqs.map((faq) => (
        <details key={faq.question} className="group">
          <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 font-semibold text-ink hover:bg-cream/50 [&::-webkit-details-marker]:hidden">
            {faq.question}
            <PlusIcon size={18} className="shrink-0 text-gold-700 transition-transform group-open:rotate-45" />
          </summary>
          <p className="px-5 pb-5 leading-8 text-ink-soft">{faq.answer}</p>
        </details>
      ))}
    </div>
  );
}
