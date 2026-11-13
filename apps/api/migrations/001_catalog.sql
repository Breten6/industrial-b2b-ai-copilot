CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE product_families (
    slug text PRIMARY KEY,
    name text NOT NULL
);

CREATE TABLE products (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    family_slug text NOT NULL REFERENCES product_families(slug),
    sku text NOT NULL UNIQUE,
    name text NOT NULL,
    description text NOT NULL,
    is_demo boolean NOT NULL DEFAULT false
);

CREATE TABLE source_documents (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id integer NOT NULL REFERENCES products(id),
    title text NOT NULL,
    revision text NOT NULL,
    is_demo boolean NOT NULL DEFAULT false,
    UNIQUE (id, product_id),
    UNIQUE (product_id, title, revision)
);

CREATE TABLE source_passages (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id integer NOT NULL REFERENCES source_documents(id),
    locator text NOT NULL,
    excerpt text NOT NULL CHECK (length(trim(excerpt)) > 0),
    UNIQUE (id, document_id),
    UNIQUE (document_id, locator)
);

CREATE TABLE spec_assertions (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id integer NOT NULL REFERENCES products(id),
    document_id integer NOT NULL,
    passage_id integer NOT NULL,
    spec_key text NOT NULL,
    label text NOT NULL,
    value text NOT NULL CHECK (length(trim(value)) > 0),
    unit text,
    review_state text NOT NULL CHECK (review_state IN ('demo', 'candidate', 'reviewed')),
    FOREIGN KEY (document_id, product_id) REFERENCES source_documents(id, product_id),
    FOREIGN KEY (passage_id, document_id) REFERENCES source_passages(id, document_id),
    UNIQUE (product_id, spec_key, passage_id)
);
