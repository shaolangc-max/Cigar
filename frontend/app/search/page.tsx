"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { getToken } from "@/lib/auth";
import { CigarSummary } from "@/lib/api";

// 升级引导 Modal
function QuotaModal({ onClose }: { onClose: () => void }) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 200,
      backgroundColor: "rgba(0,0,0,0.35)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          backgroundColor: "var(--apple-surface)",
          border: "1px solid var(--apple-border)",
          borderRadius: 20,
          padding: "32px 36px",
          maxWidth: 360,
          width: "90%",
          textAlign: "center",
          boxShadow: "0 8px 40px rgba(0,0,0,0.18)",
        }}
      >
        <div style={{ fontSize: 36, marginBottom: 12 }}>🔍</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 8px", letterSpacing: "-0.02em" }}>
          今日搜索次数已用完
        </h2>
        <p style={{ fontSize: 13, color: "var(--apple-secondary)", margin: "0 0 6px" }}>
          免费版每天可搜索 15 次
        </p>
        <p style={{ fontSize: 13, color: "var(--apple-secondary)", margin: "0 0 24px" }}>
          升级 PRO，享无限次搜索 + 价格历史趋势 + 降价提醒
        </p>
        <Link
          href="/pricing"
          style={{
            display: "block",
            backgroundColor: "var(--apple-blue)",
            color: "#fff",
            borderRadius: 12,
            padding: "12px",
            fontSize: 15,
            fontWeight: 600,
            textDecoration: "none",
            marginBottom: 10,
          }}
        >
          立即升级 PRO
        </Link>
        <button
          onClick={onClose}
          style={{
            background: "none", border: "none", cursor: "pointer",
            fontSize: 13, color: "var(--apple-tertiary)", padding: "4px",
          }}
        >
          明天再来
        </button>
      </div>
    </div>
  );
}

export default function SearchPage() {
  const initialQ = typeof window !== "undefined"
    ? new URLSearchParams(window.location.search).get("q") ?? ""
    : "";

  const [q, setQ]               = useState(initialQ);
  const [results, setResults]   = useState<CigarSummary[]>([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [quotaHit, setQuotaHit] = useState(false);
  const [error, setError]       = useState(false);

  // 页面加载时如果 URL 有 ?q= 参数，自动执行搜索
  useEffect(() => {
    if (initialQ.trim()) doSearch(initialQ);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const doSearch = useCallback(async (query: string) => {
    if (!query.trim()) return;
    setLoading(true);
    setError(false);
    setQuotaHit(false);

    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    try {
      const res = await fetch(`/api/v1/cigars?q=${encodeURIComponent(query.trim())}`, { headers });
      if (res.status === 429) {
        setQuotaHit(true);
        return;
      }
      if (!res.ok) { setError(true); return; }
      const data: CigarSummary[] = await res.json();
      setResults(data);
      setSearched(true);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    doSearch(q);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      {quotaHit && <QuotaModal onClose={() => setQuotaHit(false)} />}

      {/* Search Box */}
      <form onSubmit={handleSubmit} style={{ display: "flex", gap: 10, maxWidth: 560 }}>
        <input
          type="text"
          value={q}
          onChange={e => setQ(e.target.value)}
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
        <button
          type="submit"
          disabled={loading}
          style={{
            borderRadius: 12,
            backgroundColor: "var(--apple-blue)",
            color: "#fff",
            border: "none",
            padding: "12px 24px",
            fontSize: 15,
            fontWeight: 500,
            whiteSpace: "nowrap",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? "搜索中…" : "搜索"}
        </button>
      </form>

      {/* Results */}
      {error ? (
        <p style={{ fontSize: 15, color: "#ff3b30" }}>搜索失败，请稍后重试</p>
      ) : searched && results.length === 0 ? (
        <p style={{ fontSize: 15, color: "var(--apple-tertiary)" }}>未找到「{q}」相关结果</p>
      ) : searched && results.length > 0 ? (
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
      ) : (
        <p style={{ fontSize: 15, color: "var(--apple-tertiary)" }}>
          输入雪茄名称搜索，如 "Cohiba Robusto"、"Montecristo No.2"…
        </p>
      )}
    </div>
  );
}
