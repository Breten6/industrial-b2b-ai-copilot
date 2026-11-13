import "server-only";

export interface Specification {
  id: number;
  key: string;
  label: string;
  value: string;
  unit: string | null;
  review_state: "demo" | "reviewed";
  citation: Citation;
}

export interface Citation {
  document: string;
  revision: string;
  locator: string;
  excerpt: string;
  is_demo: boolean;
  document_id: number | null;
  page_number: number | null;
}

export interface Product {
  sku: string;
  name: string;
  family: string;
  description: string;
  is_demo: boolean;
  specifications: Specification[];
  matched_source: Citation | null;
}

export interface DocumentSummary {
  id: number;
  sku: string;
  title: string;
  revision: string;
  page_count: number;
  is_demo: boolean;
  archived: boolean;
}

export interface DocumentDetail extends DocumentSummary {
  passages: { id: number; page_number: number; locator: string; excerpt: string }[];
  assertions: {
    id: number;
    passage_id: number;
    label: string;
    value: string;
    evidence_quote: string;
    review_state: "candidate" | "reviewed" | "rejected";
  }[];
}

export function apiUrl(path: string) {
  return new URL(path, process.env.API_BASE_URL ?? "http://127.0.0.1:8000");
}

async function readApi<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(apiUrl(path), { cache: "no-store", signal: AbortSignal.timeout(28_000) });
    if (!response.ok) return null;
    return await response.json() as T;
  } catch {
    return null;
  }
}

export async function searchCatalog(query: string) {
  const data = await readApi<{ products: Product[] }>(`/v1/catalog?q=${encodeURIComponent(query)}`);
  return data?.products ?? null;
}

export async function compareCatalog(skus: string[]) {
  const params = new URLSearchParams();
  for (const sku of skus) params.append("sku", sku);
  const data = await readApi<{ products: Product[] }>(`/v1/compare?${params}`);
  return data?.products ?? null;
}

export const listDocuments = () => readApi<DocumentSummary[]>("/v1/documents");
export const readDocument = (id: string) => readApi<DocumentDetail>(`/v1/documents/${id}`);
