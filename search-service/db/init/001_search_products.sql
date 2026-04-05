CREATE TABLE IF NOT EXISTS search_products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT,
    price INT,
    rating FLOAT,
    review_count INT,
    stock INT,
    category TEXT,
    content TEXT,
    author TEXT,
    publisher TEXT,
    publication_year INT,
    language TEXT,
    cover_type TEXT,
    page_count INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_search_products_normalized_name ON search_products (normalized_name);
CREATE INDEX IF NOT EXISTS idx_search_products_price ON search_products (price);
CREATE INDEX IF NOT EXISTS idx_search_products_rating ON search_products (rating);
CREATE INDEX IF NOT EXISTS idx_search_products_review_count ON search_products (review_count);
CREATE INDEX IF NOT EXISTS idx_search_products_stock ON search_products (stock);
CREATE INDEX IF NOT EXISTS idx_search_products_category ON search_products (category);
CREATE INDEX IF NOT EXISTS idx_search_products_author ON search_products (author);
CREATE INDEX IF NOT EXISTS idx_search_products_publisher ON search_products (publisher);
CREATE INDEX IF NOT EXISTS idx_search_products_publication_year ON search_products (publication_year);
CREATE INDEX IF NOT EXISTS idx_search_products_language ON search_products (language);
CREATE INDEX IF NOT EXISTS idx_search_products_cover_type ON search_products (cover_type);
CREATE INDEX IF NOT EXISTS idx_search_products_page_count ON search_products (page_count);
