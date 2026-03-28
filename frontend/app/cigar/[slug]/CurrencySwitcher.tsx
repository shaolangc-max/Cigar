"use client";

import { useRouter } from "next/navigation";
import { Currency } from "@/lib/api";

const CURRENCIES: Currency[] = ["USD", "CNY", "HKD", "EUR"];

export default function CurrencySwitcher({ current, slug }: { current: Currency; slug: string }) {
  const router = useRouter();

  return (
    <div style={{
      display: "flex",
      gap: 4,
      padding: "4px",
      borderRadius: 12,
      backgroundColor: "var(--apple-fill)",
      border: "1px solid var(--apple-border)",
    }}>
      {CURRENCIES.map((c) => (
        <button
          key={c}
          onClick={() => router.push(`/cigar/${slug}?currency=${c}`)}
          style={{
            borderRadius: 9,
            padding: "6px 14px",
            fontSize: 13,
            fontWeight: 500,
            border: "none",
            cursor: "pointer",
            transition: "all 0.15s",
            backgroundColor: current === c ? "var(--apple-surface)" : "transparent",
            color: current === c ? "var(--apple-label)" : "var(--apple-secondary)",
            boxShadow: current === c ? "0 1px 4px rgba(0,0,0,0.10)" : "none",
          }}
        >
          {c}
        </button>
      ))}
    </div>
  );
}
