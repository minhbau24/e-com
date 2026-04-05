"""Manual chatbot API test runner.

This runner lives at workspace level and tests e-com chatbot through HTTP API.

Options:
1) Run 10 fixed test prompts.
2) Ask custom questions interactively.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from urllib import error as urlerror
from urllib import request as urlrequest


FIXED_TEST_QUERIES = [
    "Gợi ý cho tôi 3 sách kiến trúc cơ bản cho người mới.",
    "Sách kiến trúc nào đang còn hàng?",
    "Tìm sách kiến trúc dưới 800k còn hàng top 3 rating cao.",
    "Cho tôi sách của tác giả Claudia Martinez Alonso.",
    "Giá và tồn kho của sách Architecture 101 là bao nhiêu?",
    "So sánh nhanh 2 sách kiến trúc nổi bật trong tầm giá 500k-1tr.",
    "Có sách bìa cứng tiếng Anh xuất bản sau năm 2015 không?",
    "Gợi ý sách về interior design cho người đi làm.",
    "Sách nào review cao và số lượng đánh giá nhiều?",
    "Nếu tôi muốn quà tặng sách kiến trúc, nên chọn cuốn nào?",
]


@dataclass
class TestResult:
    query: str
    ok: bool
    elapsed_seconds: float
    intent: str | None
    response_text: str
    error: str | None


def _is_result_ok(result: dict) -> tuple[bool, str | None]:
    if result.get("error"):
        return False, str(result["error"])

    response = str(result.get("response", "")).strip()
    if not response:
        return False, "Empty response"

    if response.lower().startswith("[error]"):
        return False, response

    return True, None


def _post_chat(base_url: str, query: str, user_id: str, timeout_seconds: float, debug: bool) -> dict:
    payload = {
        "user_id": user_id,
        "query": query,
        "debug": debug,
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    api_url = f"{base_url.rstrip('/')}/chat"

    req = urlrequest.Request(
        api_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    with urlrequest.urlopen(req, timeout=timeout_seconds) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def _run_one_query(
    base_url: str,
    query: str,
    user_id: str = "test-user",
    timeout_seconds: float = 30.0,
    debug: bool = True,
) -> TestResult:
    start = time.perf_counter()
    try:
        payload = _post_chat(
            base_url=base_url,
            query=query,
            user_id=user_id,
            timeout_seconds=timeout_seconds,
            debug=debug,
        )
        ok, error_message = _is_result_ok(payload)
        response_text = str(payload.get("response", "")).strip()
        return TestResult(
            query=query,
            ok=ok,
            elapsed_seconds=time.perf_counter() - start,
            intent=payload.get("intent"),
            response_text=response_text,
            error=error_message,
        )
    except urlerror.HTTPError as exc:
        details = ""
        try:
            details = exc.read().decode("utf-8", errors="replace")
        except Exception:
            details = str(exc)
        return TestResult(
            query=query,
            ok=False,
            elapsed_seconds=time.perf_counter() - start,
            intent=None,
            response_text="",
            error=f"HTTP {exc.code}: {details}",
        )
    except urlerror.URLError as exc:
        return TestResult(
            query=query,
            ok=False,
            elapsed_seconds=time.perf_counter() - start,
            intent=None,
            response_text="",
            error=f"Cannot connect to API ({base_url}): {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive for manual tool
        return TestResult(
            query=query,
            ok=False,
            elapsed_seconds=time.perf_counter() - start,
            intent=None,
            response_text="",
            error=str(exc),
        )


def run_fixed_tests(base_url: str, timeout_seconds: float, debug: bool) -> int:
    print("\n=== Running 10 fixed chatbot API tests ===")
    print(f"Base URL: {base_url}")
    results: list[TestResult] = []

    for index, query in enumerate(FIXED_TEST_QUERIES, start=1):
        print(f"\n[{index}/10] Query: {query}")
        result = _run_one_query(
            base_url=base_url,
            query=query,
            user_id=f"fixed-test-{index}",
            timeout_seconds=timeout_seconds,
            debug=debug,
        )
        results.append(result)

        if result.ok:
            print(f"  PASS | intent={result.intent} | {result.elapsed_seconds:.2f}s")
            print("  Response:")
            print(result.response_text)
        else:
            print(f"  FAIL | intent={result.intent} | {result.elapsed_seconds:.2f}s")
            print(f"  Error: {result.error}")

    passed = sum(1 for item in results if item.ok)
    failed = len(results) - passed
    print("\n=== Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    return 0 if failed == 0 else 1


def run_single_query(base_url: str, query: str, timeout_seconds: float, debug: bool, user_id: str = "single-test") -> int:
    """Run exactly one query and print the full response."""
    print("\n=== Running single chatbot API test ===")
    print(f"Base URL: {base_url}")
    print(f"Query: {query}")

    result = _run_one_query(
        base_url=base_url,
        query=query,
        user_id=user_id,
        timeout_seconds=timeout_seconds,
        debug=debug,
    )

    if result.ok:
        print(f"PASS | intent={result.intent} | {result.elapsed_seconds:.2f}s")
        print("Response:")
        print(result.response_text)
        return 0

    print(f"FAIL | intent={result.intent} | {result.elapsed_seconds:.2f}s")
    print(f"Error: {result.error}")
    return 1


def list_fixed_queries() -> None:
    print("\n=== Fixed test queries ===")
    for index, query in enumerate(FIXED_TEST_QUERIES, start=1):
        print(f"{index}. {query}")


def run_interactive_mode(base_url: str, timeout_seconds: float, debug: bool) -> int:
    print("\n=== Interactive chatbot API test mode ===")
    print(f"Base URL: {base_url}")
    print("Type your question and press Enter.")
    print("Type 'exit' or 'quit' to stop.\n")

    turn = 1
    while True:
        try:
            question = input(f"Q{turn}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            return 0

        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            print("Bye.")
            return 0

        result = _run_one_query(
            base_url=base_url,
            query=question,
            user_id="interactive-user",
            timeout_seconds=timeout_seconds,
            debug=debug,
        )
        if result.ok:
            print(f"A{turn} (intent={result.intent}, {result.elapsed_seconds:.2f}s):")
            print(result.response_text)
        else:
            print(f"A{turn} ERROR ({result.elapsed_seconds:.2f}s): {result.error}")
        print()
        turn += 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Chatbot API test runner")
    parser.add_argument(
        "--mode",
        choices=["fixed", "interactive", "single"],
        default="fixed",
        help="Test mode (default: fixed).",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of e-com API (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30).",
    )
    parser.add_argument(
        "--no-debug",
        action="store_true",
        help="Do not send debug=true in API payload.",
    )
    parser.add_argument(
        "--query-index",
        type=int,
        help="Run only one fixed query by 1-based index.",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Run a custom query directly instead of a fixed query.",
    )
    parser.add_argument(
        "--list-queries",
        action="store_true",
        help="List the fixed queries and exit.",
    )
    args = parser.parse_args()

    debug = not args.no_debug

    if args.list_queries:
        list_fixed_queries()
        return 0

    if args.query:
        return run_single_query(args.base_url, args.query, args.timeout, debug)

    if args.query_index is not None:
        if args.query_index < 1 or args.query_index > len(FIXED_TEST_QUERIES):
            print(f"Invalid --query-index {args.query_index}. Use 1..{len(FIXED_TEST_QUERIES)}.")
            return 2
        selected_query = FIXED_TEST_QUERIES[args.query_index - 1]
        return run_single_query(
            base_url=args.base_url,
            query=selected_query,
            timeout_seconds=args.timeout,
            debug=debug,
            user_id=f"fixed-test-{args.query_index}",
        )

    if args.mode == "fixed":
        return run_fixed_tests(args.base_url, args.timeout, debug)
    if args.mode == "single":
        print("Please provide --query or --query-index when using --mode single.")
        return 2
    return run_interactive_mode(args.base_url, args.timeout, debug)


if __name__ == "__main__":
    sys.exit(main())
