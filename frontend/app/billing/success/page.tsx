"use client";

import { useEffect, useState } from "react";
import { getToken, apiMe, saveUser } from "@/lib/auth";

export default function BillingSuccessPage() {
  const [done, setDone] = useState(false);

  // 付款成功后，重新拉取用户信息（此时 webhook 应已更新订阅状态）
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    apiMe(token)
      .then(user => { saveUser(user); setDone(true); })
      .catch(() => setDone(true));
  }, []);

  return (
    <div style={{ maxWidth: 480, margin: "80px auto", textAlign: "center" }}>
      <div style={{ fontSize: 56, marginBottom: 24 }}>🎉</div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 12, letterSpacing: "-0.02em" }}>
        订阅成功！
      </h1>
      <p style={{ color: "var(--apple-secondary)", fontSize: 15, lineHeight: 1.7, marginBottom: 36 }}>
        感谢你的支持。PRO 功能现在已为你开启，<br />
        包括价格历史趋势图和降价提醒。
      </p>
      {done && (
        <a
          href="/"
          style={{
            display: "inline-block",
            padding: "12px 32px",
            backgroundColor: "var(--apple-blue)",
            color: "#fff",
            borderRadius: 10,
            textDecoration: "none",
            fontSize: 15,
            fontWeight: 500,
          }}
        >
          开始使用
        </a>
      )}
    </div>
  );
}
