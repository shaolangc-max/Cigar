import Link from "next/link";
import { notFound } from "next/navigation";
import { api, BrandDetail } from "@/lib/api";

export const revalidate = 300;

export default async function BrandPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let brand: BrandDetail;
  try {
    brand = await api.brand(slug);
  } catch {
    notFound();
  }

  const totalCigars = brand.series.reduce((s, sr) => s + sr.cigars.length, 0);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="text-xs text-zinc-400 flex gap-1.5 items-center">
        <Link href="/" className="hover:text-zinc-600">品牌</Link>
        <span>/</span>
        <span className="text-zinc-700">{brand.name}</span>
      </nav>

      {/* Brand Header */}
      <div className="flex items-end gap-4">
        <div>
          <h1 className="text-2xl font-bold">{brand.name}</h1>
          <p className="text-sm text-zinc-400 mt-0.5">{totalCigars} 款 · {brand.country ?? "Cuba"}</p>
        </div>
      </div>

      {/* Series + Cigars */}
      {brand.series.map((sr) => (
        <div key={sr.slug}>
          <h2 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-3">
            {sr.name}
          </h2>
          <div className="grid gap-2">
            {sr.cigars.map((c) => (
              <Link
                key={c.slug}
                href={`/cigar/${c.slug}`}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-4 py-3 hover:border-zinc-400 hover:shadow-sm transition-all"
              >
                <div>
                  <div className="font-medium text-sm">{c.name}</div>
                  {c.vitola && (
                    <div className="text-xs text-zinc-400 mt-0.5">{c.vitola}</div>
                  )}
                </div>
                <div className="text-right">
                  {c.min_price_single != null && (
                    <div className="text-sm font-medium text-zinc-800">
                      单支 {c.currency} {c.min_price_single.toFixed(2)}起
                    </div>
                  )}
                  {c.min_price_box != null && (
                    <div className="text-xs text-zinc-500">
                      盒 {c.currency} {c.min_price_box.toFixed(2)}起
                    </div>
                  )}
                  {c.min_price_single == null && c.min_price_box == null && (
                    <span className="text-xs text-zinc-300">暂无报价</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
