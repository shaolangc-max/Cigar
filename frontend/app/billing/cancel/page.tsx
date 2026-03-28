export default function BillingCancelPage() {
  return (
    <div style={{ maxWidth: 480, margin: "80px auto", textAlign: "center" }}>
      <div style={{ fontSize: 56, marginBottom: 24 }}>↩️</div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 12, letterSpacing: "-0.02em" }}>
        已取消支付
      </h1>
      <p style={{ color: "var(--apple-secondary)", fontSize: 15, lineHeight: 1.7, marginBottom: 36 }}>
        你已取消本次支付，未产生任何费用。<br />
        随时可以重新订阅。
      </p>
      <a
        href="/pricing"
        style={{
          display: "inline-block",
          padding: "12px 32px",
          backgroundColor: "var(--apple-label)",
          color: "#fff",
          borderRadius: 10,
          textDecoration: "none",
          fontSize: 15,
          fontWeight: 500,
        }}
      >
        返回定价页
      </a>
    </div>
  );
}
