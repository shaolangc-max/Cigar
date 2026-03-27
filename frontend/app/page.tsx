import Link from "next/link";
import { api, Brand } from "@/lib/api";

export const revalidate = 300;

export default async function Home() {
  let brands: Brand[] = [];
  try {
    brands = await api.brands();
  } catch {
    // backend not ready yet — show empty state
  }

  return (
    <div className="space-y-8">
      {/* Hero / Search */}
      <div className="rounded-2xl bg-white border border-zinc-200 px-6 py-10 text-center shadow-sm">
        <h1 className="text-2xl font-bold tracking-tight">古巴雪茄全球比价</h1>
        <p className="mt-2 text-sm text-zinc-500">
          实时抓取 60+ 欧港美专卖店价格，支持 USD / CNY / HKD / EUR 换算
        </p>
        <form action="/search" className="mt-6 flex gap-2 max-w-md mx-auto">
          <input
            name="q"
            type="text"
            placeholder="搜索雪茄名称，如 Cohiba Robusto…"
            className="flex-1 rounded-lg border border-zinc-300 px-4 py-2 text-sm outline-none focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500"
          />
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white hover:bg-zinc-700 transition-colors"
          >
            搜索
          </button>
        </form>
      </div>

      {/* Brand Grid */}
      <div>
        <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-widest mb-4">
          古巴品牌
        </h2>
        {brands.length === 0 ? (
          <p className="text-sm text-zinc-400">数据加载中…</p>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {brands.map((b) => (
              <Link
                key={b.slug}
                href={`/brand/${b.slug}`}
                className="flex flex-col gap-1 rounded-xl border border-zinc-200 bg-white px-4 py-4 shadow-sm hover:border-zinc-400 hover:shadow transition-all"
              >
                <span className="font-medium text-sm leading-tight">{b.name}</span>
                {b.cigar_count > 0 && (
                  <span className="text-xs text-zinc-400">{b.cigar_count} 款</span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
