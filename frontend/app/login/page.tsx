"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiLogin, apiMe, saveToken, saveUser } from "@/lib/auth";

const GOOGLE_AUTH_URL =
  "https://accounts.google.com/o/oauth2/v2/auth?" +
  new URLSearchParams({
    client_id:     "484821651625-pdm2svo3afsvk5jkivcscee27fb6vgju.apps.googleusercontent.com",
    redirect_uri:  "http://localhost:3001/auth/google-callback",
    response_type: "code",
    scope:         "openid email profile",
    access_type:   "online",
    hl:            "zh-CN",
  }).toString();

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { access_token } = await apiLogin({ email, password });
      saveToken(access_token);
      const user = await apiMe(access_token);
      saveUser(user);
      window.location.href = "/";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 400, margin: "60px auto" }}>
      <h1 style={{ fontSize: 24, fontWeight: 600, marginBottom: 8, letterSpacing: "-0.02em" }}>
        登录
      </h1>
      <p style={{ color: "var(--apple-secondary)", fontSize: 14, marginBottom: 28 }}>
        没有账号？<a href="/register" style={{ color: "var(--apple-blue)", textDecoration: "none" }}>免费注册</a>
      </p>

      {/* Google 登录按钮 */}
      <button
        type="button"
        onClick={() => { window.location.href = GOOGLE_AUTH_URL; }}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 10,
          padding: "11px 16px",
          border: "1px solid var(--apple-border)",
          borderRadius: 10,
          backgroundColor: "var(--apple-surface)",
          color: "var(--apple-label)",
          textDecoration: "none",
          fontSize: 15,
          fontWeight: 500,
          marginBottom: 20,
          width: "100%",
          cursor: "pointer",
        }}
      >
        <GoogleIcon />
        使用 Google 账号登录
      </button>

      {/* 分隔线 */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <div style={{ flex: 1, height: 1, backgroundColor: "var(--apple-separator)" }} />
        <span style={{ fontSize: 12, color: "var(--apple-tertiary)" }}>或使用邮箱登录</span>
        <div style={{ flex: 1, height: 1, backgroundColor: "var(--apple-separator)" }} />
      </div>

      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label style={{ display: "block", fontSize: 13, color: "var(--apple-secondary)", marginBottom: 6 }}>
            邮箱
          </label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            placeholder="you@example.com"
            style={inputStyle}
          />
        </div>

        <div>
          <label style={{ display: "block", fontSize: 13, color: "var(--apple-secondary)", marginBottom: 6 }}>
            密码
          </label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            placeholder="输入密码"
            style={inputStyle}
          />
        </div>

        {error && (
          <p style={{ color: "#FF3B30", fontSize: 13, margin: 0 }}>{error}</p>
        )}

        <button
          type="submit"
          disabled={loading}
          style={btnStyle(loading)}
        >
          {loading ? "登录中…" : "登录"}
        </button>
      </form>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  border: "1px solid var(--apple-border)",
  borderRadius: 10,
  fontSize: 15,
  backgroundColor: "var(--apple-surface)",
  color: "var(--apple-label)",
  outline: "none",
  boxSizing: "border-box",
};

const btnStyle = (loading: boolean): React.CSSProperties => ({
  padding: "12px",
  backgroundColor: "var(--apple-blue)",
  color: "#fff",
  border: "none",
  borderRadius: 10,
  fontSize: 15,
  fontWeight: 500,
  cursor: loading ? "not-allowed" : "pointer",
  opacity: loading ? 0.6 : 1,
  marginTop: 4,
});

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18">
      <path fill="#4285F4" d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z"/>
      <path fill="#EA4335" d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 7.293C4.672 5.166 6.656 3.58 9 3.58z"/>
    </svg>
  );
}
