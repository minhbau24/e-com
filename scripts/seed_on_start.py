import time
from pathlib import Path

import requests

from import_products import import_books


def wait_for_service(url: str, timeout_seconds: int = 90) -> None:
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code < 500:
                return
        except requests.RequestException:
            pass
        time.sleep(2)
    raise TimeoutError(f"Service not ready after {timeout_seconds}s: {url}")


def main() -> None:
    csv_path = Path("product.csv")
    if not csv_path.exists():
        raise FileNotFoundError("product.csv not found in workspace root")

    print("[INFO] seed_on_start: waiting for services...")

    wait_for_service("http://book-service:8000/books/")
    wait_for_service("http://catalog-service:8000/catalog/")

    import_books(
        csv_path=csv_path,
        book_service_url="http://book-service:8000",
        catalog_service_url="http://catalog-service:8000",
    )
    print("[INFO] seed_on_start: product and catalog seed completed")
    print("[INFO] seed_on_start: all initialization steps completed")


if __name__ == "__main__":
    main()
