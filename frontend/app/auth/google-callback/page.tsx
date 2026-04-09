"use client";

export const dynamic = "force-dynamic";

import { Suspense } from "react";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { saveToken, saveUser, apiMe } from "@/lib/auth";

function GoogleCallbackInner() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    const code  = params.get("code");
    const errParam = params.get("error");

    if (errParam || !code) {
      setError("Google 授权被取消或失败，请重试");
      return;
    }

    fetch("/api/v1/auth/google/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code,
        redirect_uri: `${window.location.origin}/auth/google-callback`,
      }),
    })
      .then(res => res.json().then(data => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.detail ?? "登录失败");
        saveToken(data.access_token);
        return apiMe(data.access_token);
      })
      .then(user => {
        saveUser(user);
        window.location.href = "/";
      })
      .catch(err => {
        setError(err.message ?? "登录失败，请重试");
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
      <p style={{ color: "var(--apple-secondary)", fontSize: 15 }}>正在登录，请稍候…</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div style={{ maxWidth: 400, margin: "80px auto", textAlign: "center" }}>
      <p style={{ color: "var(--apple-secondary)", fontSize: 15 }}>正在登录，请稍候…</p>
    </div>}>
      <GoogleCallbackInner />
    </Suspense>
  );
}
