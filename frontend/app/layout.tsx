import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geist = Geist({ variable: "--font-geist", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "古巴雪茄比价 | Cuban Cigar Prices",
  description: "实时对比全球60+专卖店古巴雪茄价格",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`${geist.variable} h-full`}>
      <body className="min-h-screen bg-zinc-50 text-zinc-900 font-[family-name:var(--font-geist)] antialiased">
        <header className="border-b border-zinc-200 bg-white sticky top-0 z-10">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <a href="/" className="text-lg font-semibold tracking-tight">
              🥃 古巴雪茄比价
            </a>
            <nav className="flex gap-6 text-sm text-zinc-500">
              <a href="/" className="hover:text-zinc-900 transition-colors">品牌</a>
              <a href="/search" className="hover:text-zinc-900 transition-colors">搜索</a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mt-16 border-t border-zinc-200 py-6 text-center text-xs text-zinc-400">
          价格每4小时自动更新 · 仅供参考，请以各网站实际价格为准
        </footer>
      </body>
    </html>
  );
}
