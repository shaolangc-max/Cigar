import Link from "next/link";
import { api, CigarSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q = "" } = await searchParams;
  let results: CigarSummary[] = [];
  let error = false;

  if (q.trim().length >= 1) {
    try {
      results = await api.search(q.trim());
    } catch {
      error = true;
    }
  }

  return (
    <div className="space-y-6">
      {/* Search Box */}
      <form action="/search" className="flex gap-2 max-w-lg">
        <input
          name="q"
          type="text"
          defaultValue={q}
          placeholder="搜索雪茄名称…"
          autoFocus
          className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
        />
        <button
          type="submit"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white hover:bg-zinc-700 transition-colors"
        >
          搜索
        </button>
      </form>

      {/* Results */}
      {q.trim() && (
        <div>
          {error ? (
            <p className="text-sm text-red-500">搜索失败，请稍后重试</p>
          ) : results.length === 0 ? (
            <p className="text-sm text-zinc-400">未找到 "{q}" 相关结果</p>
          ) : (
            <>
              <p className="text-xs text-zinc-400 mb-3">找到 {results.length} 条结果</p>
              <div className="grid gap-2">
                {results.map((c) => (
                  <Link
                    key={c.slug}
                    href={`/cigar/${c.slug}`}
                    className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3 hover:border-zinc-400 hover:shadow-sm transition-all"
                  >
                    <div>
                      <div className="font-medium text-sm">{c.name}</div>
                      <div className="text-xs text-zinc-400 mt-0.5">
                        {c.brand} · {c.series}
                        {c.vitola && ` · ${c.vitola}`}
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      {c.min_price_single != null && (
                        <div className="font-medium text-zinc-700">
                          {c.currency} {c.min_price_single.toFixed(2)}
                        </div>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {!q.trim() && (
        <p className="text-sm text-zinc-400">
          输入雪茄名称搜索，如 "Cohiba Robusto"、"Montecristo No.2"…
        </p>
      )}
    </div>
  );
}
