import Link from "next/link";
import Image from "next/image";
import { existsSync } from "fs";
import { join } from "path";
import { notFound } from "next/navigation";
import { api, BrandDetail, SeriesGroup } from "@/lib/api";

export const revalidate = 300;

export default async function BrandPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let brand: BrandDetail;
  try {
    brand = await api.brand(slug);
  } catch {
    notFound();
  }

  const totalCigars = [
    ...brand.categories.flatMap(c => c.series),
    ...brand.series,
  ].reduce((s, sr) => s + sr.cigars.length, 0);

  const hasLogo = existsSync(join(process.cwd(), "public", "brands", `${slug}.jpg`));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 40 }}>

      {/* Breadcrumb */}
      <nav style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 13, color: "var(--apple-tertiary)" }}>
        <Link href="/" style={{ color: "var(--apple-blue)", textDecoration: "none" }}>品牌</Link>
        <span>/</span>
        <span style={{ color: "var(--apple-label)" }}>{brand.name}</span>
      </nav>

      {/* Brand Header */}
      <div style={{
        borderRadius: 20,
        backgroundColor: "var(--apple-surface)",
        border: "1px solid var(--apple-border)",
        padding: "36px 40px",
        boxShadow: "0 2px 20px rgba(0,0,0,0.05)",
        display: "flex",
        alignItems: "center",
        gap: 32,
      }}>
        {hasLogo && (
          <div style={{ flexShrink: 0, width: 100, height: 100, position: "relative" }}>
            <Image src={`/brands/${slug}.jpg`} alt={brand.name} fill style={{ objectFit: "contain" }} />
          </div>
        )}
        <div>
          <h1 style={{ fontSize: 34, fontWeight: 700, letterSpacing: "-0.03em", margin: 0 }}>{brand.name}</h1>
          <p style={{ marginTop: 8, fontSize: 15, color: "var(--apple-secondary)" }}>
            {totalCigars} 款 &nbsp;·&nbsp; {brand.country ?? "Cuba"}
          </p>
        </div>
      </div>

      {/* 有分类的系列 */}
      {brand.categories.map((cat) => (
        <div key={cat.id}>
          {/* 大类标题 */}
          <div style={{
            fontSize: 13, fontWeight: 700, color: "var(--apple-label)",
            letterSpacing: "0.01em", margin: "0 0 16px 2px",
            paddingBottom: 8,
            borderBottom: "2px solid var(--apple-label)",
            display: "inline-block",
          }}>
            {cat.name}
          </div>

          {/* 大类下的各系列 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {cat.series.map((sr) => (
              <SeriesBlock key={sr.id} series={sr} />
            ))}
          </div>
        </div>
      ))}

      {/* 未分类的系列（平铺） */}
      {brand.series.map((sr) => (
        <SeriesBlock key={sr.id} series={sr} />
      ))}

    </div>
  );
}

function SeriesBlock({ series: sr }: { series: SeriesGroup }) {
  if (sr.cigars.length === 0) return null;
  return (
    <div>
      <p style={{
        fontSize: 11, fontWeight: 600, color: "var(--apple-tertiary)",
        letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 10px 4px",
      }}>
        {sr.name}
      </p>
      <div style={{
        borderRadius: 16,
        border: "1px solid var(--apple-border)",
        backgroundColor: "var(--apple-surface)",
        overflow: "hidden",
        boxShadow: "0 1px 6px rgba(0,0,0,0.04)",
      }}>
        {sr.cigars.map((c, i) => (
          <Link
            key={c.slug}
            href={`/cigar/${c.slug}`}
            className="apple-row-link"
            style={{
              padding: "14px 20px",
              borderTop: i === 0 ? "none" : "1px solid var(--apple-separator)",
            }}
          >
            <div>
              <div style={{ fontWeight: 500, fontSize: 15, color: "var(--apple-label)" }}>{c.name}</div>
              {c.vitola && (
                <div style={{ fontSize: 12, color: "var(--apple-tertiary)", marginTop: 2 }}>{c.vitola}</div>
              )}
            </div>
            <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 16 }}>
              {c.min_price_single != null && (
                <div style={{ fontSize: 14, fontWeight: 500, color: "var(--apple-label)" }}>
                  单支 {c.currency} {c.min_price_single.toFixed(2)} 起
                </div>
              )}
              {c.min_price_box != null && (
                <div style={{ fontSize: 12, color: "var(--apple-secondary)", marginTop: 2 }}>
                  盒 {c.currency} {c.min_price_box.toFixed(2)} 起
                </div>
              )}
              {c.min_price_single == null && c.min_price_box == null && (
                <span style={{ fontSize: 13, color: "var(--apple-tertiary)" }}>暂无报价</span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
