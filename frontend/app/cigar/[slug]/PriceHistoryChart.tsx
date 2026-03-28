"use client";

import { useEffect, useState, useMemo } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from "recharts";
import { isPro } from "@/lib/auth";

interface HistoryPoint {
  source_id: number;
  price_single: number | null;
  price_box: number | null;
  scraped_at: string;
}

interface ChartPoint {
  date: string;
  [key: string]: number | null | string;
}

type Range = "7d" | "30d" | "all";

const LINE_COLORS = [
  "#007AFF", "#34C759", "#FF9500", "#AF52DE",
  "#FF3B30", "#5AC8FA", "#FFCC00", "#FF2D55",
];

const RANGE_OPTIONS: { label: string; value: Range }[] = [
  { label: "7天",  value: "7d"  },
  { label: "30天", value: "30d" },
  { label: "全部", value: "all" },
];

function formatDate(iso: string) {
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function aggregateToChart(rows: HistoryPoint[], sources: Record<number, string>): ChartPoint[] {
  const map = new Map<string, ChartPoint>();
  for (const row of rows) {
    const date = formatDate(row.scraped_at);
    if (!map.has(date)) map.set(date, { date });
    const point = map.get(date)!;
    const name = sources[row.source_id] ?? `#${row.source_id}`;
    if (row.price_single != null) point[name] = row.price_single;
  }
  return Array.from(map.values());
}

export default function PriceHistoryChart({
  cigarId,
  currency,
  sources,
}: {
  cigarId: number;
  currency: string;
  sources: Record<number, string>;
}) {
  const [rawData, setRawData] = useState<HistoryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [pro, setPro]         = useState(false);
  const [range, setRange]     = useState<Range>("30d");

  useEffect(() => {
    setPro(isPro());
    fetch(`/api/v1/prices/history/${cigarId}?currency=${currency}`)
      .then(r => r.json())
      .then((rows: HistoryPoint[]) => setRawData(rows))
      .finally(() => setLoading(false));
  }, [cigarId, currency]);

  // 按选中时间范围过滤
  const filteredData = useMemo<ChartPoint[]>(() => {
    if (rawData.length === 0) return [];
    const now = Date.now();
    const cutoff = range === "7d"  ? now - 7  * 86400_000
                 : range === "30d" ? now - 30 * 86400_000
                 : 0;
    const filtered = rawData.filter(r => new Date(r.scraped_at).getTime() >= cutoff);
    // 所选范围没数据时自动回退到全部
    const rows = filtered.length > 0 ? filtered : rawData;
    return aggregateToChart(rows, sources);
  }, [rawData, range, sources]);

  const sourceNames = useMemo(() =>
    Array.from(new Set(filteredData.flatMap(d => Object.keys(d).filter(k => k !== "date")))),
    [filteredData]
  );

  // 判断所选范围是否有数据（用于显示回退提示）
  const rangeEmpty = useMemo(() => {
    if (rawData.length === 0 || range === "all") return false;
    const now = Date.now();
    const cutoff = range === "7d" ? now - 7 * 86400_000 : now - 30 * 86400_000;
    return rawData.filter(r => new Date(r.scraped_at).getTime() >= cutoff).length === 0;
  }, [rawData, range]);

  if (loading) {
    return (
      <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 13, color: "var(--apple-tertiary)" }}>加载中…</span>
      </div>
    );
  }

  if (rawData.length === 0) {
    return (
      <div style={{ height: 120, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontSize: 13, color: "var(--apple-tertiary)" }}>暂无历史数据</span>
      </div>
    );
  }

  return (
    <div style={{ position: "relative" }}>

      {/* 时间范围筛选 + 回退提示 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        {RANGE_OPTIONS.map(opt => (
          <button
            key={opt.value}
            onClick={() => setRange(opt.value)}
            style={{
              padding: "4px 14px",
              borderRadius: 20,
              border: "1px solid",
              borderColor: range === opt.value ? "var(--apple-blue)" : "var(--apple-border)",
              backgroundColor: range === opt.value ? "var(--apple-blue)" : "transparent",
              color: range === opt.value ? "#fff" : "var(--apple-secondary)",
              fontSize: 12,
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            {opt.label}
          </button>
        ))}
        {rangeEmpty && (
          <span style={{ fontSize: 11, color: "var(--apple-tertiary)", marginLeft: 4 }}>
            该时段暂无数据，已显示全部
          </span>
        )}
      </div>

      {/* 图表本体，非 PRO 时模糊 */}
      <div style={{
        filter: pro ? "none" : "blur(5px)",
        pointerEvents: pro ? "auto" : "none",
        userSelect: pro ? "auto" : "none",
        transition: "filter 0.3s",
      }}>
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={filteredData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--apple-separator)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: "var(--apple-tertiary)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "var(--apple-tertiary)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={v => `${v}`}
              width={48}
            />
            <Tooltip
              contentStyle={{
                borderRadius: 10,
                border: "1px solid var(--apple-border)",
                backgroundColor: "var(--apple-surface)",
                fontSize: 12,
              }}
              formatter={(value: number) => [`${currency} ${value.toFixed(2)}`, ""]}
            />
            <Legend
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: 12, paddingTop: 12 }}
            />
            {sourceNames.map((name, i) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={LINE_COLORS[i % LINE_COLORS.length]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 非 PRO 遮罩 */}
      {!pro && (
        <div style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <div style={{
            backgroundColor: "var(--apple-surface)",
            border: "1px solid var(--apple-border)",
            borderRadius: 16,
            padding: "20px 28px",
            textAlign: "center",
            boxShadow: "0 4px 24px rgba(0,0,0,0.10)",
          }}>
            <div style={{ fontSize: 22, marginBottom: 6 }}>🔒</div>
            <p style={{ fontSize: 14, fontWeight: 600, color: "var(--apple-label)", margin: "0 0 4px" }}>
              PRO 专属：价格历史趋势
            </p>
            <p style={{ fontSize: 12, color: "var(--apple-secondary)", margin: "0 0 16px" }}>
              查看各平台价格走势，找准最低价时机
            </p>
            <a
              href="/pricing"
              style={{
                display: "inline-block",
                backgroundColor: "var(--apple-blue)",
                color: "#fff",
                borderRadius: 10,
                padding: "8px 24px",
                fontSize: 13,
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              解锁 PRO
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
