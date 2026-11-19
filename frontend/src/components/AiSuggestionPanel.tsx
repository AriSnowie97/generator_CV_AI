"use client";

import { Check, Sparkles, X } from "@/components/Icons";

interface AiSuggestionPanelProps {
  title: string;
  variants: string[];
  disclaimer: string;
  onAccept: (variant: string) => void;
  onReject: () => void;
}

export function AiSuggestionPanel({
  title,
  variants,
  disclaimer,
  onAccept,
  onReject,
}: AiSuggestionPanelProps) {
  if (!variants.length) return null;

  return (
    <div className="mt-3 rounded-xl border border-blue-200 bg-blue-50/70 p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5 text-sm font-semibold text-blue-900">
          <Sparkles className="h-4 w-4 text-blue-600" />
          <span>{title}</span>
        </div>
        <button
          type="button"
          onClick={onReject}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-slate-600 hover:bg-white"
        >
          <X className="h-3.5 w-3.5" />
          Відхилити всі
        </button>
      </div>

      <p className="mt-1 text-xs text-blue-800">{disclaimer}</p>

      <div className="mt-3 space-y-2">
        {variants.map((variant, index) => (
          <div
            key={index}
            className="flex flex-col justify-between gap-2 rounded-lg border border-blue-100 bg-white p-3 sm:flex-row sm:items-center"
          >
            <p className="text-sm text-slate-800">{variant}</p>
            <button
              type="button"
              onClick={() => onAccept(variant)}
              className="inline-flex shrink-0 items-center justify-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
            >
              <Check className="h-3.5 w-3.5" />
              Прийняти
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
