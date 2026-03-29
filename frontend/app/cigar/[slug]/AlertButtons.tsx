"use client";

import { useEffect, useRef, useState } from "react";
import { getToken, isPro } from "@/lib/auth";

interface AlertOut {
  id: number;
  alert_type: string;
  target_price: number | null;
  currency: string;
}

const PRO_CTA = (
  <div style={{
    marginTop: 8,
    padding: "12px 16px",
    borderRadius: 12,
    border: "1px solid var(--apple-border)",
    backgroundColor: "var(--apple-surface)",
    boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
  }}>
    <div>
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--apple-label)", margin: "0 0 2px" }}>
        ⚡ PRO 专属功能
      </p>
      <p style={{ fontSize: 12, color: "var(--apple-secondary)", margin: 0 }}>
        升级后可设置提醒，第一时间获取通知
      </p>
    </div>
    <a
      href="/pricing"
      style={{
        flexShrink: 0,
        backgroundColor: "var(--apple-blue)",
        color: "#fff",
        borderRadius: 8,
        padding: "7px 16px",
        fontSize: 13,
        fontWeight: 600,
        textDecoration: "none",
        whiteSpace: "nowrap",
      }}
    >
      解锁 PRO
    </a>
  </div>
);

export default function AlertButtons({
  cigarId,
  currency,
}: {
  cigarId: number;
  currency: string;
}) {
  const [pro, setPro]                       = useState(false);
  const [alerts, setAlerts]                 = useState<AlertOut[]>([]);
  const [openPanel, setOpenPanel]           = useState<"price" | "stock" | null>(null);
  const [targetPrice, setTargetPrice]       = useState("");
  const [priceCurrency, setPriceCurrency]   = useState(currency);
  const [loading, setLoading]               = useState(false);
  const containerRef                        = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setPro(isPro());
  }, []);

  useEffect(() => {
    if (!openPanel) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [openPanel]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    fetch(`/api/v1/alerts?cigar_id=${cigarId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.ok ? r.json() : [])
      .then(setAlerts);
  }, [cigarId]);

  const activeAlert = (type: string) => alerts.find(a => a.alert_type === type);

  async function toggleStock() {
    const existing = activeAlert("stock");
    const token = getToken()!;
    setLoading(true);
    try {
      if (existing) {
        await fetch(`/api/v1/alerts/${existing.id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        setAlerts(prev => prev.filter(a => a.id !== existing.id));
      } else {
        const res = await fetch("/api/v1/alerts", {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ cigar_id: cigarId, alert_type: "stock" }),
        });
        if (res.ok) {
          const created = await res.json();
          setAlerts(prev => [...prev, created]);
        }
      }
      setOpenPanel(null);
    } finally {
      setLoading(false);
    }
  }

  async function savePrice() {
    const val = parseFloat(targetPrice);
    if (isNaN(val) || val <= 0) return;
    const token = getToken()!;
    setLoading(true);
    try {
      const existing = activeAlert("price");
      if (existing) {
        await fetch(`/api/v1/alerts/${existing.id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
      }
      const res = await fetch("/api/v1/alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          cigar_id: cigarId,
          alert_type: "price",
          target_price: val,
          currency: priceCurrency,
        }),
      });
      if (res.ok) {
        const created = await res.json();
        setAlerts(prev => [...prev.filter(a => a.alert_type !== "price"), created]);
      }
      setOpenPanel(null);
      setTargetPrice("");
    } finally {
      setLoading(false);
    }
  }

  async function cancelPrice() {
    const existing = activeAlert("price");
    if (!existing) return;
    const token = getToken()!;
    setLoading(true);
    try {
      await fetch(`/api/v1/alerts/${existing.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      setAlerts(prev => prev.filter(a => a.id !== existing.id));
      setOpenPanel(null);
    } finally {
      setLoading(false);
    }
  }

  const hasStock = !!activeAlert("stock");
  const hasPrice = !!activeAlert("price");
  const priceAlert = activeAlert("price");

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>

        {/* 降价提醒按钮 */}
        <button
          onClick={() => setOpenPanel(openPanel === "price" ? null : "price")}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "8px 14px",
            borderRadius: 10,
            border: `1px solid ${hasPrice ? "var(--apple-blue)" : "var(--apple-border)"}`,
            backgroundColor: hasPrice ? "rgba(0,122,255,0.08)" : "var(--apple-surface)",
            color: hasPrice ? "var(--apple-blue)" : "var(--apple-secondary)",
            fontSize: 13, fontWeight: 500, cursor: "pointer",
          }}
        >
          🔔 {hasPrice ? `降价提醒已设置` : "降价提醒"}
        </button>

        {/* 到货提醒按钮 */}
        <button
          onClick={() => {
            if (!pro) { setOpenPanel(openPanel === "stock" ? null : "stock"); return; }
            toggleStock();
          }}
          disabled={loading && pro}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "8px 14px",
            borderRadius: 10,
            border: `1px solid ${hasStock ? "#34C759" : "var(--apple-border)"}`,
            backgroundColor: hasStock ? "rgba(52,199,89,0.08)" : "var(--apple-surface)",
            color: hasStock ? "#1a7f3c" : "var(--apple-secondary)",
            fontSize: 13, fontWeight: 500, cursor: "pointer",
          }}
        >
          📦 {hasStock ? "到货提醒已订阅" : "到货提醒"}
        </button>
      </div>

      {/* 展开面板（绝对定位，不撑高父容器） */}
      {openPanel === "stock" && !pro && (
        <div style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 20, minWidth: 320 }}>{PRO_CTA}</div>
      )}

      {openPanel === "price" && !pro && (
        <div style={{ position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 20, minWidth: 320 }}>{PRO_CTA}</div>
      )}

      {openPanel === "price" && pro && (
        <div style={{
          position: "absolute", top: "calc(100% + 8px)", right: 0, zIndex: 20,
          padding: "16px",
          borderRadius: 12,
          border: "1px solid var(--apple-border)",
          backgroundColor: "var(--apple-surface)",
          boxShadow: "0 2px 12px rgba(0,0,0,0.07)",
          minWidth: 320,
        }}>
          <p style={{ fontSize: 13, fontWeight: 600, margin: "0 0 12px", color: "var(--apple-label)" }}>
            🔔 设置目标价
          </p>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, color: "var(--apple-secondary)" }}>低于</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={targetPrice}
              onChange={e => setTargetPrice(e.target.value)}
              placeholder="0.00"
              style={{
                width: 90, padding: "7px 10px",
                borderRadius: 8, border: "1px solid var(--apple-border)",
                fontSize: 14, backgroundColor: "var(--apple-bg)",
                color: "var(--apple-label)", outline: "none",
              }}
            />
            <select
              value={priceCurrency}
              onChange={e => setPriceCurrency(e.target.value)}
              style={{
                padding: "7px 10px", borderRadius: 8,
                border: "1px solid var(--apple-border)",
                fontSize: 13, backgroundColor: "var(--apple-bg)",
                color: "var(--apple-label)",
              }}
            >
              {["USD","CNY","HKD","EUR"].map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            <span style={{ fontSize: 13, color: "var(--apple-secondary)" }}>时通知我</span>
          </div>

          {priceAlert && (
            <p style={{ fontSize: 12, color: "var(--apple-tertiary)", margin: "8px 0 0" }}>
              当前：{priceAlert.currency} {priceAlert.target_price?.toFixed(2)}
            </p>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
            <button
              onClick={savePrice}
              disabled={loading}
              style={{
                padding: "7px 20px", borderRadius: 8,
                backgroundColor: "var(--apple-blue)", color: "#fff",
                border: "none", fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              {loading ? "保存中…" : "保存提醒"}
            </button>
            {hasPrice && (
              <button
                onClick={cancelPrice}
                disabled={loading}
                style={{
                  padding: "7px 16px", borderRadius: 8,
                  backgroundColor: "transparent",
                  border: "1px solid var(--apple-border)",
                  color: "#FF3B30", fontSize: 13, cursor: "pointer",
                }}
              >
                取消提醒
              </button>
            )}
            <button
              onClick={() => setOpenPanel(null)}
              style={{
                padding: "7px 12px", borderRadius: 8,
                backgroundColor: "transparent",
                border: "none",
                color: "var(--apple-tertiary)", fontSize: 13, cursor: "pointer",
              }}
            >
              关闭
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
