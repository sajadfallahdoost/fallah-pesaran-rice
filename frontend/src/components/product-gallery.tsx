"use client";

import Image from "next/image";
import { useState } from "react";

import type { ImageRef } from "@/lib/types";

export function ProductGallery({ images, name }: { images: ImageRef[]; name: string }) {
  const [active, setActive] = useState(0);
  const current = images[active];
  if (!current) {
    return (
      <div className="flex aspect-square items-center justify-center rounded-[var(--radius-card)] bg-cream text-ink-muted">
        بدون تصویر
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <div className="relative aspect-square overflow-hidden rounded-[var(--radius-card)] border border-line bg-cream">
        <Image
          src={current.url}
          alt={current.alt || name}
          fill
          preload
          sizes="(min-width: 1024px) 560px, 100vw"
          className="object-cover"
          quality={80}
        />
      </div>
      {images.length > 1 && (
        <div className="flex gap-3" role="group" aria-label="تصاویر محصول">
          {images.map((image, index) => (
            <button
              key={image.url}
              type="button"
              onClick={() => setActive(index)}
              aria-label={`تصویر ${index + 1}: ${image.alt}`}
              aria-pressed={index === active}
              className={`relative size-20 overflow-hidden rounded-xl border-2 bg-cream transition-colors sm:size-24 ${
                index === active ? "border-green-800" : "border-transparent hover:border-line"
              }`}
            >
              <Image src={image.url} alt="" fill sizes="96px" className="object-cover" quality={70} />
            </button>
          ))}
        </div>
      )}
      {images.some((image) => image.is_generated_sample) && (
        <p className="text-xs text-ink-muted">تصاویر نمایشی‌اند و ممکن است با بستهٔ واقعی تفاوت داشته باشند.</p>
      )}
    </div>
  );
}
