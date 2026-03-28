"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getUser, logout, type AuthUser } from "@/lib/auth";

export default function HeaderNav() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);

  // 每次页面挂载时从 localStorage 读取用户信息
  useEffect(() => {
    setUser(getUser());
  }, []);

  function handleLogout() {
    logout();
    setUser(null);
    router.push("/");
    router.refresh();
  }

  return (
    <nav style={{ display: "flex", alignItems: "center", gap: 20 }}>
      <a href="/" className="apple-nav-link" style={{ fontSize: 14 }}>品牌</a>
      <a href="/search" className="apple-nav-link" style={{ fontSize: 14 }}>搜索</a>
      <a href="/pricing" className="apple-nav-link" style={{ fontSize: 14 }}>订阅</a>

      {user ? (
        // 已登录：显示头像/昵称 + 注销按钮
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt="avatar"
                referrerPolicy="no-referrer"
                style={{ width: 28, height: 28, borderRadius: "50%", objectFit: "cover" }}
              />
            ) : (
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                backgroundColor: "var(--apple-blue)", color: "#fff",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 12, fontWeight: 600,
              }}>
                {(user.nickname ?? user.email)[0].toUpperCase()}
              </div>
            )}
            <span style={{ fontSize: 13, color: "var(--apple-secondary)" }}>
              {user.subscription_status === "pro" && (
                <span style={{
                  fontSize: 10,
                  backgroundColor: "var(--apple-blue)",
                  color: "#fff",
                  borderRadius: 4,
                  padding: "1px 5px",
                  marginRight: 6,
                  fontWeight: 600,
                }}>PRO</span>
              )}
              {user.nickname ?? user.email.split("@")[0]}
            </span>
          </div>
          <button
            onClick={handleLogout}
            style={{
              fontSize: 13,
              color: "var(--apple-secondary)",
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 0,
            }}
          >
            注销
          </button>
        </div>
      ) : (
        // 未登录：显示登录按钮
        <a
          href="/login"
          style={{
            fontSize: 13,
            color: "#fff",
            backgroundColor: "var(--apple-blue)",
            borderRadius: 8,
            padding: "5px 14px",
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          登录
        </a>
      )}
    </nav>
  );
}
