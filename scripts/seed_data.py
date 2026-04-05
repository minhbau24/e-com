import argparse
import os
import subprocess
import sys
import shutil
from pathlib import Path


def run_cmd(command, cwd=None, env=None):
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    printable_cwd = str(cwd) if cwd else str(Path.cwd())
    print(f"[INFO] Running in {printable_cwd}: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, env=merged_env, check=True)


def resolve_default_csv(root_dir: Path) -> Path:
    candidates = [
        root_dir / "product.csv",
        root_dir / "e-com-service" / "data" / "product.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def seed_search(root_dir: Path, source_csv: Path, database_url: str, table_name: str, limit: int) -> None:
    script_path = root_dir / "search-service" / "scripts" / "import_products.py"
    if not script_path.exists():
        raise FileNotFoundError(f"search import script not found: {script_path}")

    command = [
        sys.executable,
        str(script_path),
        "--source",
        str(source_csv),
        "--database-url",
        database_url,
        "--table",
        table_name,
    ]
    if limit > 0:
        command.extend(["--limit", str(limit)])

    run_cmd(
        command,
        cwd=root_dir,
    )


def seed_kb(root_dir: Path, source_csv: Path, database_url: str, skip_if_no_google_key: bool) -> None:
    ecom_dir = root_dir / "e-com-service"
    if not ecom_dir.exists():
        raise FileNotFoundError(f"e-com-service folder not found: {ecom_dir}")

    data_dir = ecom_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    staged_csv = data_dir / source_csv.name
    if source_csv.resolve() != staged_csv.resolve():
        shutil.copy2(source_csv, staged_csv)
        print(f"[INFO] Staged KB source CSV to {staged_csv}")

    google_api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if skip_if_no_google_key and not google_api_key:
        print("[WARN] GOOGLE_API_KEY is empty. Skipping KB build.")
        return

    run_cmd(
        [sys.executable, "-m", "kb.build_kb"],
        cwd=ecom_dir,
        env={
            "PYTHONPATH": str(ecom_dir),
            "POSTGRES_URL": database_url,
        },
    )


def main() -> None:
    root_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(
        description="Unified seed runner for this workspace (search data + KB embeddings)."
    )
    parser.add_argument(
        "--source",
        "--csv",
        default=str(resolve_default_csv(root_dir)),
        help="Path to source product CSV",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv(
            "POSTGRES_URL",
            "postgresql://ecom_user:ecom_password@localhost:5432/ecom_db",
        ),
        help="PostgreSQL connection URL for both search and KB",
    )
    parser.add_argument(
        "--search-table",
        default=os.getenv("SEARCH_PRODUCTS_TABLE", "search_products"),
        help="Target table for search-service seed",
    )
    parser.add_argument(
        "--products",
        type=int,
        default=20,
        help="Number of product rows to seed into search (0 means all)",
    )
    parser.add_argument(
        "--only",
        choices=["all", "search", "kb"],
        default="all",
        help="Run only one seed step or all",
    )
    parser.add_argument(
        "--skip-if-no-google-key",
        action="store_true",
        help="Skip KB step when GOOGLE_API_KEY is empty",
    )
    args = parser.parse_args()

    source_csv = Path(args.source)
    if not source_csv.exists():
        raise SystemExit(f"Source CSV not found: {source_csv}")

    if not args.database_url.strip():
        raise SystemExit("--database-url (or POSTGRES_URL env) is required")

    print("[INFO] Starting unified seed process...")
    print(f"[INFO] source_csv={source_csv}")
    print(f"[INFO] database_url={args.database_url}")

    if args.only in {"all", "search"}:
        print("[INFO] Step 1/2: Seeding search_products...")
        seed_search(
            root_dir=root_dir,
            source_csv=source_csv,
            database_url=args.database_url,
            table_name=args.search_table,
            limit=args.products,
        )

    if args.only in {"all", "kb"}:
        print("[INFO] Step 2/2: Building KB embeddings...")
        seed_kb(
            root_dir=root_dir,
            source_csv=source_csv,
            database_url=args.database_url,
            skip_if_no_google_key=args.skip_if_no_google_key,
        )

    print("[INFO] Unified seed completed.")


if __name__ == "__main__":
    main()
