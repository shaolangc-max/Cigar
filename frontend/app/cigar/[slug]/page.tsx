"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, CigarDetail, Currency, PriceRow } from "@/lib/api";

const CURRENCIES: Currency[] = ["USD", "CNY", "HKD", "EUR"];

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  USD: "$", CNY: "¥", HKD: "HK$", EUR: "€",
};

function PriceCell({ value, currency }: { value: number | null; currency: Currency }) {
  if (value == null) return <span className="text-zinc-300">—</span>;
  return (
    <span>
      {CURRENCY_SYMBOLS[currency]}{value.toFixed(2)}
    </span>
  );
}

function StockBadge({ inStock }: { inStock: boolean }) {
  return inStock ? (
    <span className="inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 ring-1 ring-green-200">
      有货
    </span>
  ) : (
    <span className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-400">
      缺货
    </span>
  );
}

export default function CigarPage() {
  const { slug } = useParams<{ slug: string }>();
  const [currency, setCurrency] = useState<Currency>("USD");
  const [data, setData] = useState<CigarDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const d = await api.cigar(slug, currency);
      setData(d);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [slug, currency]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="py-20 text-center text-sm text-zinc-400">加载中…</div>
    );
  }

  if (error || !data) {
    return (
      <div className="py-20 text-center">
        <p className="text-zinc-500">未找到该雪茄</p>
        <Link href="/" className="mt-4 inline-block text-sm text-zinc-700 underline">返回首页</Link>
      </div>
    );
  }

  // Separate in-stock from out-of-stock rows
  const inStockRows  = data.prices.filter((p) => p.in_stock);
  const outStockRows = data.prices.filter((p) => !p.in_stock);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-xs text-zinc-400 flex gap-1.5 items-center flex-wrap">
        <Link href="/" className="hover:text-zinc-600">品牌</Link>
        <span>/</span>
        <Link href={`/brand/${data.brand.slug}`} className="hover:text-zinc-600">
          {data.brand.name}
        </Link>
        <span>/</span>
        <span className="text-zinc-700">{data.name}</span>
      </nav>

      {/* Cigar Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl font-bold leading-tight">{data.name}</h1>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-zinc-500">
            {data.vitola    && <span>{data.vitola}</span>}
            {data.length_mm && <span>{data.length_mm}mm</span>}
            {data.ring_gauge && <span>环径 {data.ring_gauge}</span>}
          </div>
        </div>

        {/* Currency Switcher */}
        <div className="flex gap-1">
          {CURRENCIES.map((c) => (
            <button
              key={c}
              onClick={() => setCurrency(c)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                currency === c
                  ? "bg-zinc-900 text-white"
                  : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* Price Table */}
      {data.prices.length === 0 ? (
        <div className="rounded-xl border border-zinc-200 bg-white px-6 py-12 text-center text-sm text-zinc-400">
          暂无报价数据
        </div>
      ) : (
        <div className="space-y-4">
          <PriceTable rows={inStockRows}  currency={currency} title="有货商家" />
          {outStockRows.length > 0 && (
            <PriceTable rows={outStockRows} currency={currency} title="缺货商家" dimmed />
          )}
        </div>
      )}
    </div>
  );
}

function PriceTable({
  rows, currency, title, dimmed = false,
}: {
  rows: PriceRow[];
  currency: Currency;
  title: string;
  dimmed?: boolean;
}) {
  if (rows.length === 0) return null;

  return (
    <div>
      <h2 className={`text-xs font-semibold uppercase tracking-wider mb-2 ${dimmed ? "text-zinc-300" : "text-zinc-500"}`}>
        {title} ({rows.length})
      </h2>
      <div className="overflow-x-auto rounded-xl border border-zinc-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-100 text-xs text-zinc-400">
              <th className="px-4 py-2.5 text-left font-medium">网站</th>
              <th className="px-4 py-2.5 text-right font-medium">单支价</th>
              <th className="px-4 py-2.5 text-right font-medium">盒装价</th>
              <th className="px-4 py-2.5 text-right font-medium">支数</th>
              <th className="px-4 py-2.5 text-center font-medium">库存</th>
            </tr>
          </thead>
          <tbody className={dimmed ? "opacity-40" : ""}>
            {rows.map((p, i) => (
              <tr
                key={p.source_slug}
                className={`border-b border-zinc-50 last:border-0 hover:bg-zinc-50 transition-colors ${
                  i === 0 && !dimmed ? "bg-green-50/50" : ""
                }`}
              >
                <td className="px-4 py-3">
                  {p.product_url ? (
                    <a
                      href={p.product_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium hover:underline text-zinc-800"
                    >
                      {p.source_name}
                    </a>
                  ) : (
                    <span className="font-medium text-zinc-800">{p.source_name}</span>
                  )}
                  <div className="text-[10px] text-zinc-400 mt-0.5">
                    {new Date(p.scraped_at).toLocaleDateString("zh-CN")}
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  <PriceCell value={p.price_single} currency={currency} />
                </td>
                <td className="px-4 py-3 text-right font-medium">
                  <PriceCell value={p.price_box} currency={currency} />
                </td>
                <td className="px-4 py-3 text-right text-zinc-500">
                  {p.box_count ?? "—"}
                </td>
                <td className="px-4 py-3 text-center">
                  <StockBadge inStock={p.in_stock} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
