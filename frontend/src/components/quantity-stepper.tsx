"use client";

import { MinusIcon, PlusIcon } from "@/components/icons";
import { faDigits } from "@/lib/format";

export function QuantityStepper({
  value,
  max,
  onChange,
  disabled = false,
  label,
}: {
  value: number;
  max: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  label: string;
}) {
  const atMax = value >= max;
  return (
    <div className="inline-flex items-center rounded-xl border-[1.5px] border-line bg-white" role="group" aria-label={label}>
      <button
        type="button"
        className="flex size-11 items-center justify-center rounded-s-xl text-green-800 hover:bg-green-50 disabled:opacity-40"
        onClick={() => onChange(value + 1)}
        disabled={disabled || atMax}
        aria-label="افزایش تعداد"
      >
        <PlusIcon size={18} />
      </button>
      <output className="min-w-10 text-center font-bold tabular" aria-live="polite">
        {faDigits(value)}
      </output>
      <button
        type="button"
        className="flex size-11 items-center justify-center rounded-e-xl text-green-800 hover:bg-green-50 disabled:opacity-40"
        onClick={() => onChange(value - 1)}
        disabled={disabled || value <= 1}
        aria-label="کاهش تعداد"
      >
        <MinusIcon size={18} />
      </button>
    </div>
  );
}
