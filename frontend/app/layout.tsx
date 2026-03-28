import type { Metadata } from "next";
import "./globals.css";
import HeaderNav from "./components/HeaderNav";

export const metadata: Metadata = {
  title: "海淘研究院 | 古巴雪茄比价",
  description: "实时对比全球60+专卖店古巴雪茄价格",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
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
            <a href="/" style={{ color: "var(--apple-label)", fontSize: 17, fontWeight: 600, letterSpacing: "-0.02em", textDecoration: "none" }}>
              海淘研究院
            </a>
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
        </footer>
      </body>
    </html>
  );
}
