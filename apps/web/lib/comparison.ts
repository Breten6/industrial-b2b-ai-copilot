import type { Product, Specification } from "./catalog";

export function comparisonRows(products: Product[]) {
  const labels = new Map<string, string>();
  for (const product of products) {
    for (const specification of product.specifications) {
      labels.set(specification.key, specification.label);
    }
  }
  return [...labels].sort((left, right) => left[1].localeCompare(right[1])).map(([key, label]) => ({
    key,
    label,
    cells: products.map((product) => product.specifications.filter((specification) => specification.key === key)),
  }));
}

export function displayValue(specification: Specification) {
  return [specification.value, specification.unit].filter(Boolean).join(" ");
}

export function hasConflictingValues(specifications: Specification[]) {
  return new Set(specifications.map(displayValue)).size > 1;
}
