"use client";

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { saveToken, saveUser, apiMe } from "@/lib/auth";

function AuthCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    const token = params.get("token");
    const err   = params.get("error");

    if (err || !token) {
      setError("Google 登录失败，请重试");
      return;
    }

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
        <Link href="/login" style={{ color: "var(--apple-blue)", fontSize: 14 }}>返回登录页</Link>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", textAlign: "center" }}>
      <p style={{ color: "var(--apple-secondary)", fontSize: 15 }}>登录中，请稍候…</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div style={{ maxWidth: 400, margin: "80px auto", textAlign: "center" }}>
      <p style={{ color: "var(--apple-secondary)", fontSize: 15 }}>登录中，请稍候…</p>
    </div>}>
      <AuthCallbackInner />
    </Suspense>
  );
}
