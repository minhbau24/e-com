from scripts.import_products import (
    extract_page_count,
    extract_year,
    infer_language,
    normalize_cover_type,
    normalize_text,
    parse_product_row,
)


def test_parse_product_row_extracts_book_metadata():
    row = {
        "id": "278805060",
        "name": "Sách - Bathrooms: Architecture Today by Claudia Martinez Alonso | Architecture Book - Bìa cứng",
        "price": "780000",
        "short_description": "Tác giả: Claudia Martinez AlonsoNhà xuất bản: KoenemannNăm xuất bản: 2016Loại bìa: Bìa cứngSố trang: 504 TrangNgôn ngữ: Tiếng AnhISBN: 9783864075834Kích thước: 23.88 x 3.56 x 23.88 cm",
        "description": "Tác giả: Claudia Martinez AlonsoNhà xuất bản: KoenemannNăm xuất bản: 2016Loại bìa: Bìa cứngSố trang: 504 TrangNgôn ngữ: Tiếng AnhISBN: 9783864075834Kích thước: 23.88 x 3.56 x 23.88 cm",
        "rating_average": "0",
        "review_count": "0",
        "stock": "1000",
    }

    product = parse_product_row(row)

    assert product.product_id == "278805060"
    assert product.normalized_name == "sach bathrooms architecture today by claudia martinez alonso architecture book bia cung"
    assert product.author == "Claudia Martinez Alonso"
    assert product.publisher == "Koenemann"
    assert product.publication_year == 2016
    assert product.cover_type == "Bìa cứng"
    assert product.page_count == 504
    assert product.language == "Tiếng Anh"
    assert product.stock == 1000


def test_parse_product_row_handles_concatenated_metadata_without_spaces():
    row = {
        "id": "1",
        "name": "Book",
        "price": "10",
        "short_description": "Tác giả: A.B.Nhà xuất bản: X.Năm xuất bản: 2020.Loại bìa: Bìa mềm.Số trang: 120 Trang.Ngôn ngữ: Tiếng Việt.ISBN: 123456.Kích thước: 10 x 20 cm",
        "description": "Tác giả: A.B.Nhà xuất bản: X.Năm xuất bản: 2020.Loại bìa: Bìa mềm.Số trang: 120 Trang.Ngôn ngữ: Tiếng Việt.ISBN: 123456.Kích thước: 10 x 20 cm",
    }

    product = parse_product_row(row)

    assert product.author == "A.B."
    assert product.publisher == "X."
    assert product.publication_year == 2020
    assert product.cover_type == "Bìa mềm"
    assert product.page_count == 120


def test_metadata_helpers_handle_common_patterns():
    text = "Author: Tomris Tangaz Publication date: 06 Sep 2018 Format: Paperback | 144 pages"

    assert normalize_text("  Sách  Kiến  Trúc ") == "sach kien truc"
    assert extract_year(text) == 2018
    assert extract_page_count(text) == 144
    assert infer_language("Ngôn ngữ: Tiếng Việt") == "Tiếng Việt"
    assert normalize_cover_type("Paperback") == "Bìa mềm"
