"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { saveToken, saveUser, apiMe } from "@/lib/auth";

/**
 * Google OAuth 回调页
 * 后端授权完成后会重定向到：/auth/callback?token=xxx
 * 本页读取 token，存入 localStorage，然后跳回首页
 */
export default function AuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = params.get("token");
    const err   = params.get("error");

    if (err || !token) {
      setError("Google 登录失败，请重试");
      return;
    }

    // 存 token，再拉取用户信息
    saveToken(token);
    apiMe(token)
      .then(user => {
        saveUser(user);
        router.replace("/");
      })
      .catch(() => {
        setError("获取用户信息失败，请重新登录");
      });
  }, [params, router]);

  if (error) {
    return (
      <div style={{ maxWidth: 400, margin: "80px auto", textAlign: "center" }}>
        <p style={{ color: "#FF3B30", fontSize: 15, marginBottom: 24 }}>{error}</p>
        <a href="/login" style={{ color: "var(--apple-blue)", fontSize: 14 }}>返回登录页</a>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", textAlign: "center" }}>
      <p style={{ color: "var(--apple-secondary)", fontSize: 15 }}>登录中，请稍候…</p>
    </div>
  );
}
