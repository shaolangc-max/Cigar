const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001/api/v1";

export type Currency = "USD" | "CNY" | "HKD" | "EUR";

// ── Types ──────────────────────────────────────────────────────────────────

export interface Brand {
  id: number;
  name: string;
  slug: string;
  country: string | null;
  image_url: string | null;
  cigar_count: number;
}

export interface CigarSummary {
  id: number;
  name: string;
  slug: string;
  vitola: string | null;
  image_url: string | null;
  series: string;
  brand: string;
  brand_slug: string;
  min_price_single: number | null;
  min_price_box: number | null;
  currency: Currency;
}

export interface PriceRow {
  source_id: number;
  source_name: string;
  source_slug: string;
  base_url: string;
  product_url: string | null;
  currency: Currency;
  price_single: number | null;
  price_box: number | null;
  box_count: number | null;
  in_stock: boolean;
  scraped_at: string;
}

export interface CigarDetail {
  id: number;
  name: string;
  slug: string;
  vitola: string | null;
  length_mm: number | null;
  ring_gauge: number | null;
  image_url: string | null;
  series: { name: string; slug: string };
  brand: { name: string; slug: string };
  prices: PriceRow[];
  currency: Currency;
}

export interface BrandDetail {
  id: number;
  name: string;
  slug: string;
  country: string | null;
  image_url: string | null;
  series: {
    id: number;
    name: string;
    slug: string;
    cigars: CigarSummary[];
  }[];
}

// ── Fetch helpers ─────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 300 } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

// ── API calls ─────────────────────────────────────────────────────────────

export const api = {
  brands: (): Promise<Brand[]> => get("/brands"),
  brand:  (slug: string): Promise<BrandDetail> => get(`/brands/${slug}`),
  cigar:  (slug: string, currency: Currency = "USD"): Promise<CigarDetail> =>
    get(`/cigars/${slug}?currency=${currency}`),
  search: (q: string): Promise<CigarSummary[]> =>
    get(`/cigars?q=${encodeURIComponent(q)}`),
};
