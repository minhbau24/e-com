import argparse
import os
import subprocess
import sys
from pathlib import Path


def resolve_default_csv(root_dir: Path) -> Path:
    candidates = [
        root_dir / "product.csv",
        root_dir / "e-com-service" / "data" / "product.csv",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def run_cmd(command: list[str], cwd: Path) -> None:
    printable_cwd = str(cwd)
    print(f"[INFO] Running in {printable_cwd}: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def build_parser(root_dir: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run seed_data.py and simulate_system_via_gateway.py with synchronized inputs."
    )
    parser.add_argument(
        "--source",
        "--csv",
        default=str(resolve_default_csv(root_dir)),
        help="Path to source product CSV shared by seed and simulation",
    )
    parser.add_argument(
        "--products",
        type=int,
        default=20,
        help="Number of products to use in both seed and simulation (0 means all)",
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("POSTGRES_URL", "postgresql://ecom_user:ecom_password@localhost:5432/ecom_db"),
        help="PostgreSQL connection URL for seed_data",
    )
    parser.add_argument(
        "--search-table",
        default=os.getenv("SEARCH_PRODUCTS_TABLE", "search_products"),
        help="Target table name for search seed",
    )
    parser.add_argument(
        "--skip-if-no-google-key",
        action="store_true",
        help="Skip KB step in seed_data when GOOGLE_API_KEY is missing",
    )
    parser.add_argument("--gateway", default="http://localhost:8000", help="API Gateway URL for simulation")
    parser.add_argument("--users", type=int, default=5, help="Number of users to simulate")
    parser.add_argument("--min-items", type=int, default=1, help="Min cart items per order")
    parser.add_argument("--max-items", type=int, default=4, help="Max cart items per order")
    parser.add_argument("--orders-per-user", type=int, default=2, help="Orders per user")
    parser.add_argument("--max-retries", type=int, default=3, help="HTTP retries for simulation")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Retry delay for simulation")
    parser.add_argument("--timeout", type=int, default=8, help="HTTP timeout seconds")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for simulation")
    parser.add_argument("--seed-only", action="store_true", help="Run only seed step")
    parser.add_argument("--simulate-only", action="store_true", help="Run only simulation step")
    return parser


def main() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    args = build_parser(root_dir).parse_args()

    if args.seed_only and args.simulate_only:
        raise SystemExit("--seed-only and --simulate-only cannot be used together")

    source_csv = Path(args.source)
    if not source_csv.exists():
        raise SystemExit(f"Source CSV not found: {source_csv}")

    if not args.simulate_only:
        seed_cmd = [
            sys.executable,
            str(root_dir / "scripts" / "seed_data.py"),
            "--source",
            str(source_csv),
            "--products",
            str(args.products),
            "--database-url",
            args.database_url,
            "--search-table",
            args.search_table,
        ]
        if args.skip_if_no_google_key:
            seed_cmd.append("--skip-if-no-google-key")
        run_cmd(seed_cmd, cwd=root_dir)

    if not args.seed_only:
        simulate_cmd = [
            sys.executable,
            str(root_dir / "scripts" / "simulate_system_via_gateway.py"),
            "--source",
            str(source_csv),
            "--products",
            str(args.products),
            "--gateway",
            args.gateway,
            "--users",
            str(args.users),
            "--min-items",
            str(args.min_items),
            "--max-items",
            str(args.max_items),
            "--orders-per-user",
            str(args.orders_per_user),
            "--max-retries",
            str(args.max_retries),
            "--retry-delay",
            str(args.retry_delay),
            "--timeout",
            str(args.timeout),
            "--seed",
            str(args.seed),
        ]
        run_cmd(simulate_cmd, cwd=root_dir)

    print("[INFO] run_sync_seed_and_simulate completed.")


if __name__ == "__main__":
    main()
