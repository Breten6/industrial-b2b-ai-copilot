import { Source } from "../citation";
import { compareCatalog, searchCatalog } from "../../lib/catalog";
import { comparisonRows, displayValue, hasConflictingValues } from "../../lib/comparison";

export default async function Compare({ searchParams }: {
  searchParams: Promise<{ sku?: string | string[] }>;
}) {
  const { sku } = await searchParams;
  const selected = Array.isArray(sku) ? sku : sku ? [sku] : [];
  const valid = selected.length >= 2 && selected.length <= 4
    && new Set(selected).size === selected.length
    && selected.every((item) => /^[A-Z0-9][A-Z0-9._-]{0,39}$/.test(item));
  const [options, products] = await Promise.all([searchCatalog(""), valid ? compareCatalog(selected) : null]);
  const rows = products ? comparisonRows(products) : [];

  return (
    <main className="frame workflow-page">
      <p className="eyebrow">03 / MODEL COMPARISON</p>
      <h1>Compare models</h1>
      <p className="description">Compare cited values by specification. Missing evidence and conflicting values stay visible.</p>
      <form action="/compare" className="product workflow-form compare-form">
        <fieldset>
          <legend>Select two to four models</legend>
          {options === null && <p role="alert" className="description">The catalog is temporarily unavailable.</p>}
          <div className="compare-options">
            {options?.map((product) => (
              <label className="check" key={product.sku}>
                <input type="checkbox" name="sku" value={product.sku} defaultChecked={selected.includes(product.sku)} />
                <span>{product.name} <span className="sku">{product.sku}</span> {product.is_demo && <span className="badge">Demo</span>}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <button className="primary-button">Compare selected models</button>
      </form>
      {selected.length > 0 && !valid && <p className="form-error" role="alert">Select two to four different models.</p>}
      {valid && !products && <p className="form-error" role="alert">The selected models could not be loaded.</p>}
      {products && (
        <div className="comparison-overflow">
          <table className="comparison-table">
            <caption>Side-by-side specification evidence</caption>
            <thead><tr><th scope="col">Specification</th>{products.map((product) => (
              <th scope="col" key={product.sku}>{product.name}<br /><span className="sku">{product.sku}</span> {product.is_demo && <span className="badge">Demo</span>}</th>
            ))}</tr></thead>
            <tbody>
              {!rows.length && <tr><td colSpan={products.length + 1}>No reviewed specifications for these models.</td></tr>}
              {rows.map((row) => (
                <tr key={row.key}>
                  <th scope="row">{row.label}</th>
                  {row.cells.map((specifications, index) => (
                    <td key={products[index].sku}>
                      {!specifications.length && <span className="description">No reviewed evidence</span>}
                      {hasConflictingValues(specifications) && <p className="form-error">Conflicting values</p>}
                      {specifications.map((specification) => (
                        <div key={specification.id} className="compare-value">
                          <strong>{displayValue(specification)}</strong>
                          <Source citation={specification.citation} />
                        </div>
                      ))}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
