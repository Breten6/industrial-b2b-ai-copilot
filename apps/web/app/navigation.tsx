import Link from "next/link";

export function Navigation() {
  return (
    <header className="topbar">
      <div className="frame navigation">
        <Link href="/" className="brand">
          <span className="brand-mark" aria-hidden="true">◎</span>
          Industrial B2B AI Copilot
        </Link>
        <nav aria-label="Workspace">
          <Link href="/">Catalog</Link>
          <Link href="/documents">Datasheets</Link>
          <Link href="/compare">Compare</Link>
        </nav>
      </div>
    </header>
  );
}
