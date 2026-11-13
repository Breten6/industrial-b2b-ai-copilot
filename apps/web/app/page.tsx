import Link from "next/link";
import { searchCatalog, type Product } from "../lib/catalog";
import { Source } from "./citation";

function SonarPlot() {
  return (
    <svg className="sonar-plot" viewBox="0 0 480 270" fill="none" aria-hidden="true">
      <defs>
        <pattern id="grid" width="22" height="22" patternUnits="userSpaceOnUse">
          <path d="M22 0H0v22" stroke="#234055" strokeWidth=".6" />
        </pattern>
        <linearGradient id="sweep" x1="275" y1="150" x2="395" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#23bda9" stopOpacity="0" />
          <stop offset="1" stopColor="#23bda9" stopOpacity=".46" />
        </linearGradient>
        <linearGradient id="fade">
          <stop stopColor="white" stopOpacity="0" />
          <stop offset=".4" stopColor="white" />
        </linearGradient>
        <mask id="fade-left"><rect width="480" height="270" fill="url(#fade)" /></mask>
      </defs>
      <g mask="url(#fade-left)">
        <rect width="480" height="270" fill="url(#grid)" />
        <path d="M85 144h394M286 0v270" stroke="#375064" strokeDasharray="4 6" />
        {[28, 53, 78, 103, 128].map((r) => <circle key={r} cx="286" cy="144" r={r} stroke="#3b6976" />)}
        <path d="M286 144 282 16A128 128 0 0 1 384 62Z" fill="url(#sweep)" />
        <path d="m286 144 98-82" stroke="#4fe1cc" />
        <circle cx="286" cy="144" r="3" fill="#65e9d6" />
        <circle cx="343" cy="96" r="4" fill="#65e9d6" />
        <circle cx="343" cy="96" r="9" stroke="#65e9d6" opacity=".45" />
        <circle cx="225" cy="178" r="3" fill="#65e9d6" opacity=".65" />
        <path d="M351 90l17-14h45M218 182l-20 14h-37" stroke="#4b8790" />
        <text x="374" y="70" fill="#91bac4" fontSize="9" fontFamily="monospace">CONTACT</text>
        <text x="328" y="242" fill="#7293a9" fontSize="9" fontFamily="monospace">SUBSEA / 01</text>
      </g>
    </svg>
  );
}

function ProductCard({ product }: { product: Product }) {
  return (
    <article className="product">
      <div className="flex items-center justify-between gap-3">
        <span className="sku">{product.sku}</span>
        {product.is_demo && <span className="badge">Demo record</span>}
      </div>
      <h3>{product.name}</h3>
      <p className="description">{product.description}</p>
      <dl className="specifications">
        {product.specifications.map((spec) => (
          <div className="spec" key={spec.id}>
            <dt>{spec.label}</dt>
            <dd>{spec.value}{spec.unit ? ` ${spec.unit}` : ""}</dd>
            <dd><Source citation={spec.citation} /></dd>
          </div>
        ))}
      </dl>
      {!product.specifications.length && <p className="description">No reviewed specifications yet.</p>}
      {product.matched_source && (
        <div className="spec"><Source citation={product.matched_source} label="Matched datasheet passage" /></div>
      )}
    </article>
  );
}

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ q?: string | string[] }>;
}) {
  const { q } = await searchParams;
  const query = typeof q === "string" ? Array.from(q.trim().replaceAll("\0", "")).slice(0, 120).join("") : "";
  const products = await searchCatalog(query);

  return (
    <>
      <main className="frame">
        <section className="hero" aria-labelledby="workspace-title">
          <SonarPlot />
          <div className="hero-copy">
            <p className="eyebrow">01 / PRODUCT KNOWLEDGE</p>
            <h1 id="workspace-title">Underwater sonar<br />knowledge base</h1>
            <p>Review manufacturer datasheets, search source passages, and compare cited product specifications.</p>
          </div>
        </section>
        <div className="demo-notice">
          <strong>Evidence policy</strong>
          <span>Reviewed values appear alongside labeled demo data. Review the source before using a specification commercially.</span>
        </div>
        <section aria-labelledby="catalog-title" className="catalog">
          <div className="catalog-heading">
            <div>
              <p className="eyebrow">PRODUCT LIBRARY</p>
              <h2 id="catalog-title">Catalog records</h2>
            </div>
            <form method="get" action="/" className="search" role="search">
              <label className="sr-only" htmlFor="catalog-query">Search catalog</label>
              <input id="catalog-query" name="q" defaultValue={query} maxLength={120} placeholder="Search models, SKUs, or datasheets" />
              <button type="submit">Search</button>
            </form>
          </div>
          {products === null ? (
            <div className="empty" role="alert"><strong>Catalog temporarily unavailable</strong><p>Check that the local API and database are running, then reload.</p></div>
          ) : (
            <>
              <p className="result-count">
                {products.length} {products.length === 1 ? "result" : "results"}{query && <> for “{query}” · <Link href="/">Clear search</Link></>}
              </p>
              {products.length ? (
                <div className="product-grid">{products.map((product) => <ProductCard key={product.sku} product={product} />)}</div>
              ) : (
                <div className="empty"><strong>No matching products</strong><p>Try a product name, SKU, or category.</p></div>
              )}
            </>
          )}
        </section>
      </main>
      <footer className="frame footer"><span>Industrial B2B AI Copilot</span><span>Phase 1 · Product knowledge base</span></footer>
    </>
  );
}
