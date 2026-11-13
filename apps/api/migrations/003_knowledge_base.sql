ALTER TABLE source_documents
    ADD COLUMN asset_sha256 text CHECK (asset_sha256 ~ '^[a-f0-9]{64}$'),
    ADD COLUMN byte_size integer CHECK (byte_size > 0),
    ADD COLUMN page_count integer CHECK (page_count > 0),
    ADD COLUMN archived_at timestamptz,
    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now(),
    ADD CONSTRAINT document_asset_metadata CHECK (
        (asset_sha256 IS NULL AND byte_size IS NULL AND page_count IS NULL) OR
        (asset_sha256 IS NOT NULL AND byte_size IS NOT NULL AND page_count IS NOT NULL)
    ),
    ADD UNIQUE (product_id, asset_sha256);

ALTER TABLE source_passages ADD COLUMN page_number integer CHECK (page_number > 0);
CREATE INDEX source_passages_document ON source_passages (document_id);
CREATE INDEX source_passages_text ON source_passages USING gin (to_tsvector('simple', excerpt));

CREATE TABLE passage_embeddings (
    passage_id integer NOT NULL REFERENCES source_passages(id),
    model text NOT NULL,
    embedding vector(256) NOT NULL,
    PRIMARY KEY (passage_id, model)
);

ALTER TABLE spec_assertions ADD COLUMN evidence_quote text;
ALTER TABLE spec_assertions DROP CONSTRAINT spec_assertions_product_id_spec_key_passage_id_key;
CREATE INDEX spec_assertions_product ON spec_assertions (product_id);
ALTER TABLE spec_assertions DROP CONSTRAINT spec_assertions_review_state_check;
ALTER TABLE spec_assertions ADD CHECK (
    review_state IN ('demo', 'candidate', 'reviewed', 'rejected')
);

CREATE TABLE spec_review_events (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assertion_id integer NOT NULL REFERENCES spec_assertions(id),
    action text NOT NULL CHECK (action IN ('approve', 'correct', 'reject')),
    prior_value text NOT NULL,
    prior_quote text NOT NULL,
    resulting_value text NOT NULL,
    resulting_quote text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
