"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getToken, getUser, type AuthUser } from "@/lib/auth";

const FREE_FEATURES = [
  { label: "浏览品牌 & 实时比价", included: true },
  { label: "搜索（每24小时15次）",  included: true },
  { label: "价格历史趋势图",        included: false },
  { label: "降价提醒通知",          included: false },
];

const PRO_FEATURES = [
  { label: "浏览品牌 & 实时比价", included: true },
  { label: "无限次搜索",           included: true },
  { label: "价格历史趋势图",       included: true },
  { label: "降价提醒通知",         included: true },
];

export default function PricingPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<"monthly" | "yearly" | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setUser(getUser());
  }, []);

  const isPro = user?.subscription_status === "pro";

  async function handleSubscribe(plan: "monthly" | "yearly") {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    setError("");
    setLoading(plan);
    try {
      const res = await fetch("/api/v1/billing/checkout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "创建支付会话失败");
      window.location.href = data.checkout_url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "发生错误，请稍后再试");
      setLoading(null);
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: "0 auto" }}>
      {/* 标题 */}
      <div style={{ textAlign: "center", marginBottom: 48 }}>
        <h1 style={{ fontSize: 30, fontWeight: 700, letterSpacing: "-0.03em", marginBottom: 10 }}>
          选择套餐
        </h1>
        <p style={{ color: "var(--apple-secondary)", fontSize: 15 }}>
          免费使用基础功能，升级解锁完整体验
        </p>
      </div>

      {/* 双列卡片 */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 20,
      }}>

        {/* 免费版 */}
        <div className="apple-card" style={{ padding: 28 }}>
          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--apple-secondary)", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 10 }}>
            免费版
          </p>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 24 }}>
            <span style={{ fontSize: 36, fontWeight: 700, letterSpacing: "-0.03em" }}>¥0</span>
            <span style={{ color: "var(--apple-secondary)", fontSize: 14 }}>永久免费</span>
          </div>

          <FeatureList features={FREE_FEATURES} />

          <div style={{
            marginTop: 24,
            padding: "11px",
            borderRadius: 10,
            backgroundColor: "var(--apple-fill)",
            textAlign: "center",
            fontSize: 14,
            color: "var(--apple-secondary)",
          }}>
            {user ? "当前套餐" : "无需注册即可浏览"}
          </div>
        </div>

        {/* PRO 版 */}
        <div className="apple-card" style={{
          padding: 28,
          border: "2px solid var(--apple-blue)",
          position: "relative",
        }}>
          {/* 推荐角标 */}
          <div style={{
            position: "absolute",
            top: -13,
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "var(--apple-blue)",
            color: "#fff",
            fontSize: 11,
            fontWeight: 600,
            padding: "3px 14px",
            borderRadius: 20,
            whiteSpace: "nowrap",
          }}>
            推荐
          </div>

          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--apple-blue)", letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 10 }}>
            PRO 会员
          </p>

          {/* 月/年价格 */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 4 }}>
              <span style={{ fontSize: 36, fontWeight: 700, letterSpacing: "-0.03em" }}>¥16</span>
              <span style={{ color: "var(--apple-secondary)", fontSize: 14 }}>/月</span>
            </div>
            <div style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              backgroundColor: "rgba(0, 113, 227, 0.08)",
              borderRadius: 6,
              padding: "3px 8px",
            }}>
              <span style={{ fontSize: 13, color: "var(--apple-blue)", fontWeight: 500 }}>
                年付 ¥100
              </span>
              <span style={{ fontSize: 11, color: "var(--apple-blue)", opacity: 0.8 }}>
                省 92元 · 相当于 ¥8.3/月
              </span>
            </div>
          </div>

          <FeatureList features={PRO_FEATURES} highlight />

          {isPro ? (
            <div style={{
              marginTop: 24,
              padding: "11px",
              borderRadius: 10,
              backgroundColor: "rgba(52, 199, 89, 0.1)",
              textAlign: "center",
              fontSize: 14,
              color: "var(--apple-green)",
              fontWeight: 500,
            }}>
              ✓ 当前套餐
            </div>
          ) : (
            <div style={{ marginTop: 24, display: "flex", flexDirection: "column", gap: 10 }}>
              <button
                onClick={() => handleSubscribe("yearly")}
                disabled={!!loading}
                style={{
                  padding: "12px",
                  backgroundColor: "var(--apple-blue)",
                  color: "#fff",
                  border: "none",
                  borderRadius: 10,
                  fontSize: 15,
                  fontWeight: 500,
                  cursor: loading ? "not-allowed" : "pointer",
                  opacity: loading === "yearly" ? 0.6 : 1,
                }}
              >
                {loading === "yearly" ? "跳转中…" : "年付 ¥100"}
              </button>
              <button
                onClick={() => handleSubscribe("monthly")}
                disabled={!!loading}
                style={{
                  padding: "11px",
                  backgroundColor: "transparent",
                  color: "var(--apple-blue)",
                  border: "1px solid var(--apple-blue)",
                  borderRadius: 10,
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: loading ? "not-allowed" : "pointer",
                  opacity: loading === "monthly" ? 0.6 : 1,
                }}
              >
                {loading === "monthly" ? "跳转中…" : "月付 ¥16"}
              </button>
            </div>
          )}
        </div>
      </div>

      {error && (
        <p style={{ color: "#FF3B30", fontSize: 13, textAlign: "center", marginTop: 16 }}>
          {error}
        </p>
      )}

      {/* 底部说明 */}
      <div style={{ marginTop: 36, textAlign: "center", color: "var(--apple-tertiary)", fontSize: 12, lineHeight: 2.2 }}>
        <p>支持信用卡 / 借记卡 · 由 Stripe 提供安全支付保障</p>
        <p>订阅到期前可随时取消，不再自动续费</p>
        <p>个人信息存储于日本服务器 · 本站仅提供价格参考，不从事烟草销售</p>
      </div>
    </div>
  );
}

// ── 功能列表组件 ───────────────────────────────────────────────────────────────

function FeatureList({
  features,
  highlight = false,
}: {
  features: { label: string; included: boolean }[];
  highlight?: boolean;
}) {
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 12 }}>
      {features.map(f => (
        <li key={f.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {f.included ? (
            <span style={{ color: highlight ? "var(--apple-blue)" : "var(--apple-green)", fontSize: 15, width: 18, textAlign: "center", flexShrink: 0 }}>✓</span>
          ) : (
            <span style={{ color: "var(--apple-tertiary)", fontSize: 15, width: 18, textAlign: "center", flexShrink: 0 }}>✕</span>
          )}
          <span style={{
            fontSize: 14,
            color: f.included ? "var(--apple-label)" : "var(--apple-tertiary)",
          }}>
            {f.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
