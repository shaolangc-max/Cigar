import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import HeaderNav from "./components/HeaderNav";

export const metadata: Metadata = {
  title: "海淘研究院 | 古巴雪茄比价",
  description: "实时对比全球60+专卖店古巴雪茄价格",
};

async function getLastUpdated(): Promise<string | null> {
  try {
    const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api/v1";
    const res = await fetch(`${apiBase}/prices/last-updated`, {
      next: { revalidate: 14400 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.last_updated ?? null;
  } catch {
    return null;
  }
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const lastUpdatedIso = await getLastUpdated();
  const lastUpdatedText = lastUpdatedIso
    ? new Date(lastUpdatedIso).toLocaleString("zh-CN", {
        timeZone: "Asia/Shanghai",
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit",
      })
    : null;

  return (
    <html lang="zh-CN" className="h-full">
      <body style={{ minHeight: "100vh", backgroundColor: "var(--apple-bg)", color: "var(--apple-label)" }}>

        {/* Frosted glass nav */}
        <header style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          backgroundColor: "rgba(255,255,255,0.72)",
          backdropFilter: "saturate(180%) blur(20px)",
          WebkitBackdropFilter: "saturate(180%) blur(20px)",
          borderBottom: "1px solid var(--apple-separator)",
        }}>
          <div style={{
            maxWidth: 960,
            margin: "0 auto",
            padding: "12px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}>
            <Link href="/" style={{ color: "var(--apple-label)", fontSize: 17, fontWeight: 600, letterSpacing: "-0.02em", textDecoration: "none" }}>
              海淘研究院
            </Link>
            <HeaderNav />
          </div>
        </header>

        <main style={{ maxWidth: 960, margin: "0 auto", padding: "40px 20px" }}>
          {children}
        </main>

        <footer style={{
          marginTop: 80,
          borderTop: "1px solid var(--apple-separator)",
          padding: "28px 20px",
          textAlign: "center",
          color: "var(--apple-tertiary)",
          fontSize: 12,
        }}>
          价格每4小时自动更新 · 仅供参考，请以各网站实际价格为准
          {lastUpdatedText && (
            <span style={{ marginLeft: 12, opacity: 0.7 }}>
              · 最后更新 {lastUpdatedText}
            </span>
          )}
        </footer>
      </body>
    </html>
  );
}
