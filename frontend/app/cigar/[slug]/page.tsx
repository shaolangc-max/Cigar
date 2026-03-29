import Link from "next/link";
import { notFound } from "next/navigation";
import { api, CigarDetail, Currency, PriceRow } from "@/lib/api";
import CurrencySwitcher from "./CurrencySwitcher";
import PriceHistoryChart from "./PriceHistoryChart";
import AlertButtons from "./AlertButtons";

export const revalidate = 300;

const CURRENCY_SYMBOLS: Record<Currency, string> = {
  USD: "$", CNY: "¥", HKD: "HK$", EUR: "€",
};

function fmt(value: number | null, currency: Currency) {
  if (value == null) return "—";
  return `${CURRENCY_SYMBOLS[currency]}${value.toFixed(2)}`;
}

function StockBadge({ inStock }: { inStock: boolean }) {
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      borderRadius: 20,
      padding: "3px 10px",
      fontSize: 11,
      fontWeight: 600,
      backgroundColor: inStock ? "rgba(52,199,89,0.12)" : "var(--apple-fill)",
      color: inStock ? "#1a7f3c" : "var(--apple-tertiary)",
    }}>
      {inStock ? "有货" : "缺货"}
    </span>
  );
}

function PriceTable({ rows, currency, title, dimmed = false }: {
  rows: PriceRow[];
  currency: Currency;
  title: string;
  dimmed?: boolean;
}) {
  if (rows.length === 0) return null;

  return (
    <div>
      <p style={{
        fontSize: 12,
        fontWeight: 600,
        color: dimmed ? "var(--apple-tertiary)" : "var(--apple-secondary)",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        margin: "0 0 12px 4px",
      }}>
        {title} ({rows.length})
      </p>
      <div style={{
        borderRadius: 16,
        border: "1px solid var(--apple-border)",
        backgroundColor: "var(--apple-surface)",
        overflow: "hidden",
        boxShadow: "0 1px 6px rgba(0,0,0,0.04)",
        opacity: dimmed ? 0.45 : 1,
      }}>
        {/* Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 100px 100px 110px 56px 72px",
          padding: "10px 20px",
          borderBottom: "1px solid var(--apple-separator)",
          fontSize: 11,
          fontWeight: 600,
          color: "var(--apple-tertiary)",
          letterSpacing: "0.06em",
          textTransform: "uppercase",
        }}>
          <span>网站</span>
          <span style={{ textAlign: "right" }}>单支价</span>
          <span style={{ textAlign: "right" }}>盒装价</span>
          <span style={{ textAlign: "right" }}>原价</span>
          <span style={{ textAlign: "right" }}>支数</span>
          <span style={{ textAlign: "center" }}>库存</span>
        </div>

        {/* Rows */}
        {rows.map((p, i) => (
          <div
            key={p.source_slug}
            className={`apple-price-row${i === 0 && !dimmed ? " best" : ""}`}
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 100px 100px 110px 56px 72px",
              padding: "13px 20px",
              alignItems: "center",
              borderTop: i === 0 ? "none" : "1px solid var(--apple-separator)",
              backgroundColor: i === 0 && !dimmed ? "rgba(52,199,89,0.04)" : "transparent",
            }}
          >
            <div>
              {p.product_url ? (
                <a href={p.product_url} target="_blank" rel="noopener noreferrer" className="apple-source-link" style={{ fontWeight: 500, fontSize: 14 }}>
                  {p.source_name}
                </a>
              ) : (
                <span style={{ fontWeight: 500, fontSize: 14, color: "var(--apple-label)" }}>{p.source_name}</span>
              )}
              <div style={{ fontSize: 11, color: "var(--apple-tertiary)", marginTop: 2 }}>
                {new Date(p.scraped_at).toLocaleDateString("zh-CN")}
              </div>
            </div>

            <div style={{ textAlign: "right", fontSize: 14, fontWeight: 500, color: p.price_single != null ? "var(--apple-label)" : "var(--apple-tertiary)" }}>
              {fmt(p.price_single, currency)}
            </div>

            <div style={{ textAlign: "right", fontSize: 14, fontWeight: 500, color: p.price_box != null ? "var(--apple-label)" : "var(--apple-tertiary)" }}>
              {fmt(p.price_box, currency)}
            </div>

            <div style={{ textAlign: "right", fontSize: 12, color: "var(--apple-tertiary)" }}>
              {p.price_single_src != null
                ? `${p.source_currency} ${p.price_single_src.toFixed(2)}`
                : p.price_box_src != null
                ? `${p.source_currency} ${p.price_box_src.toFixed(2)}`
                : "—"}
            </div>

            <div style={{ textAlign: "right", fontSize: 13, color: "var(--apple-secondary)" }}>
              {p.box_count ?? "—"}
            </div>

            <div style={{ textAlign: "center" }}>
              <StockBadge inStock={p.in_stock} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const VALID_CURRENCIES: Currency[] = ["USD", "CNY", "HKD", "EUR"];

export default async function CigarPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ currency?: string }>;
}) {
  const { slug } = await params;
  const { currency: rawCurrency } = await searchParams;
  const currency: Currency = VALID_CURRENCIES.includes(rawCurrency as Currency)
    ? (rawCurrency as Currency)
    : "USD";

  let data: CigarDetail;
  try {
    data = await api.cigar(slug, currency);
  } catch {
    notFound();
  }

  const inStockRows  = data.prices.filter((p) => p.in_stock);
  const outStockRows = data.prices.filter((p) => !p.in_stock);

  // source_id → source_name 映射，传给图表组件
  const sourcesMap: Record<number, string> = {};
  for (const p of data.prices) sourcesMap[p.source_id] = p.source_name;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>

      {/* Breadcrumb */}
      <nav style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap", fontSize: 13, color: "var(--apple-tertiary)" }}>
        <Link href="/" style={{ color: "var(--apple-blue)", textDecoration: "none" }}>品牌</Link>
        <span>/</span>
        <Link href={`/brand/${data.brand.slug}`} style={{ color: "var(--apple-blue)", textDecoration: "none" }}>
          {data.brand.name}
        </Link>
        <span>/</span>
        <span style={{ color: "var(--apple-label)" }}>{data.name}</span>
      </nav>

      {/* Cigar Header */}
      <div style={{
        borderRadius: 20,
        backgroundColor: "var(--apple-surface)",
        border: "1px solid var(--apple-border)",
        padding: "32px 40px",
        boxShadow: "0 2px 20px rgba(0,0,0,0.05)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: 24,
        flexWrap: "wrap",
      }}>
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.025em", margin: 0 }}>{data.name}</h1>
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 8 }}>
            {[data.vitola, data.length_mm ? `${data.length_mm} mm` : null, data.ring_gauge ? `环径 ${data.ring_gauge}` : null]
              .filter(Boolean)
              .map((tag) => (
                <span key={tag} style={{
                  fontSize: 12,
                  fontWeight: 500,
                  color: "var(--apple-secondary)",
                  backgroundColor: "var(--apple-fill)",
                  borderRadius: 8,
                  padding: "4px 10px",
                }}>
                  {tag}
                </span>
              ))}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 12 }}>
          <CurrencySwitcher current={currency} slug={slug} />
          <AlertButtons cigarId={data.id} currency={currency} />
        </div>
      </div>

      {/* Price Tables */}
      {data.prices.length === 0 ? (
        <div style={{
          borderRadius: 16,
          border: "1px solid var(--apple-border)",
          backgroundColor: "var(--apple-surface)",
          padding: "60px 24px",
          textAlign: "center",
          fontSize: 15,
          color: "var(--apple-tertiary)",
        }}>
          暂无报价数据
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <PriceTable rows={inStockRows}  currency={currency} title="有货商家" />
          {outStockRows.length > 0 && (
            <PriceTable rows={outStockRows} currency={currency} title="缺货商家" dimmed />
          )}
        </div>
      )}

      {/* 价格历史趋势图 */}
      <div style={{
        borderRadius: 16,
        border: "1px solid var(--apple-border)",
        backgroundColor: "var(--apple-surface)",
        padding: "24px 28px",
        boxShadow: "0 1px 6px rgba(0,0,0,0.04)",
      }}>
        <p style={{
          fontSize: 12,
          fontWeight: 600,
          color: "var(--apple-secondary)",
          letterSpacing: "0.08em",
          textTransform: "uppercase",
          margin: "0 0 20px 0",
        }}>
          价格历史趋势（单支）
        </p>
        <PriceHistoryChart
          cigarId={data.id}
          currency={currency}
          sources={sourcesMap}
        />
      </div>
    </div>
  );
}
