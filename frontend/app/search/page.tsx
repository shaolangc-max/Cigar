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
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>

      {/* Search Box */}
      <form action="/search" style={{ display: "flex", gap: 10, maxWidth: 560 }}>
        <input
          name="q"
          type="text"
          defaultValue={q}
          placeholder="搜索雪茄名称…"
          autoFocus
          style={{
            flex: 1,
            borderRadius: 12,
            border: "1px solid var(--apple-border)",
            backgroundColor: "var(--apple-surface)",
            padding: "12px 18px",
            fontSize: 15,
            color: "var(--apple-label)",
            outline: "none",
            boxShadow: "0 1px 6px rgba(0,0,0,0.04)",
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

      {/* Results */}
      {q.trim() ? (
        error ? (
          <p style={{ fontSize: 15, color: "#ff3b30" }}>搜索失败，请稍后重试</p>
        ) : results.length === 0 ? (
          <p style={{ fontSize: 15, color: "var(--apple-tertiary)" }}>未找到 "{q}" 相关结果</p>
        ) : (
          <div>
            <p style={{ fontSize: 12, color: "var(--apple-tertiary)", margin: "0 0 14px 4px" }}>
              找到 {results.length} 条结果
            </p>
            <div style={{
              borderRadius: 16,
              border: "1px solid var(--apple-border)",
              backgroundColor: "var(--apple-surface)",
              overflow: "hidden",
              boxShadow: "0 1px 6px rgba(0,0,0,0.04)",
            }}>
              {results.map((c, i) => (
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
                    <div style={{ fontSize: 12, color: "var(--apple-tertiary)", marginTop: 3 }}>
                      {c.brand} · {c.series}{c.vitola ? ` · ${c.vitola}` : ""}
                    </div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 16 }}>
                    {c.min_price_single != null && (
                      <div style={{ fontSize: 14, fontWeight: 500, color: "var(--apple-label)" }}>
                        {c.currency} {c.min_price_single.toFixed(2)}
                      </div>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )
      ) : (
        <p style={{ fontSize: 15, color: "var(--apple-tertiary)" }}>
          输入雪茄名称搜索，如 "Cohiba Robusto"、"Montecristo No.2"…
        </p>
      )}
    </div>
  );
}
