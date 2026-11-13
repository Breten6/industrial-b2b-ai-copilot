INSERT INTO product_families (slug, name) VALUES ('sonar', 'Underwater sonar');

INSERT INTO products (family_slug, sku, name, description, is_demo) VALUES
    ('sonar', 'DEMO-IMG', 'Forward Imaging Sonar', 'Example catalog record for an underwater inspection workflow.', true),
    ('sonar', 'DEMO-SSS', 'Side-Scan Sonar', 'Example catalog record for a survey planning workflow.', true),
    ('sonar', 'DEMO-ALT', 'Acoustic Altimeter', 'Example catalog record for a subsea navigation workflow.', true);

INSERT INTO source_documents (product_id, title, revision, is_demo)
SELECT id, name || ' · demo source', 'Fixture 1', true FROM products WHERE is_demo;

INSERT INTO source_passages (document_id, locator, excerpt)
SELECT documents.id, 'Catalog classification', 'Product category: ' || fixture.category || '.'
FROM source_documents AS documents
JOIN products ON products.id = documents.product_id
JOIN (VALUES
    ('DEMO-IMG', 'Imaging sonar'),
    ('DEMO-SSS', 'Side-scan sonar'),
    ('DEMO-ALT', 'Acoustic altimeter')
) AS fixture(sku, category) ON fixture.sku = products.sku
WHERE documents.is_demo;

INSERT INTO spec_assertions (product_id, document_id, passage_id, spec_key, label, value, review_state)
SELECT documents.product_id, documents.id, passages.id, 'product_category', 'Category',
       rtrim(split_part(passages.excerpt, ': ', 2), '.'), 'demo'
FROM source_passages AS passages
JOIN source_documents AS documents ON documents.id = passages.document_id
WHERE documents.is_demo;
