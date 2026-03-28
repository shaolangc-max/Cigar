import Link from "next/link";
import { api, Brand } from "@/lib/api";

export const revalidate = 300;

export default async function Home() {
  let brands: Brand[] = [];
  try {
    brands = await api.brands();
  } catch {
    // backend not ready yet
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 56 }}>

      {/* Hero */}
      <div style={{
        borderRadius: 20,
        backgroundColor: "var(--apple-surface)",
        border: "1px solid var(--apple-border)",
        padding: "56px 48px",
        textAlign: "center",
        boxShadow: "0 2px 20px rgba(0,0,0,0.05)",
      }}>
        <h1 style={{ fontSize: 40, fontWeight: 700, letterSpacing: "-0.04em", margin: 0, lineHeight: 1.1 }}>
          古巴雪茄全球比价
        </h1>
        <p style={{ marginTop: 14, fontSize: 17, color: "var(--apple-secondary)", lineHeight: 1.6 }}>
          实时抓取 60+ 欧港美专卖店价格 &nbsp;·&nbsp; 支持 USD / CNY / HKD / EUR 换算
        </p>
        <form action="/search" style={{ marginTop: 32, display: "flex", gap: 10, maxWidth: 500, marginLeft: "auto", marginRight: "auto" }}>
          <input
            name="q"
            type="text"
            placeholder="搜索雪茄，如 Cohiba Robusto…"
            style={{
              flex: 1,
              borderRadius: 12,
              border: "1px solid var(--apple-border)",
              backgroundColor: "var(--apple-fill)",
              padding: "12px 18px",
              fontSize: 15,
              color: "var(--apple-label)",
              outline: "none",
            }}
          />
          <button type="submit" className="apple-btn" style={{
            borderRadius: 12,
            backgroundColor: "var(--apple-blue)",
            color: "#fff",
            border: "none",
            padding: "12px 24px",
            fontSize: 15,
            fontWeight: 500,
            whiteSpace: "nowrap",
          }}>
            搜索
          </button>
        </form>
      </div>

      {/* Brand Grid */}
      <div>
        <p style={{ fontSize: 12, fontWeight: 600, color: "var(--apple-tertiary)", letterSpacing: "0.08em", textTransform: "uppercase", margin: "0 0 20px 4px" }}>
          古巴品牌
        </p>
        {brands.length === 0 ? (
          <p style={{ fontSize: 15, color: "var(--apple-tertiary)" }}>数据加载中…</p>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(175px, 1fr))", gap: 12 }}>
            {brands.map((b) => (
              <Link
                key={b.slug}
                href={`/brand/${b.slug}`}
                className="apple-card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 5,
                  borderRadius: 16,
                  border: "1px solid var(--apple-border)",
                  backgroundColor: "var(--apple-surface)",
                  padding: "20px 22px",
                  boxShadow: "0 1px 6px rgba(0,0,0,0.04)",
                  textDecoration: "none",
                }}
              >
                <span style={{ fontWeight: 600, fontSize: 15, color: "var(--apple-label)", lineHeight: 1.3 }}>
                  {b.name}
                </span>
                {b.cigar_count > 0 && (
                  <span style={{ fontSize: 12, color: "var(--apple-tertiary)" }}>{b.cigar_count} 款</span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
