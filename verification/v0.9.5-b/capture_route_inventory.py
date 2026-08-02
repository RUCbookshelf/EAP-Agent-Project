"""v0.9.5-B route-inventory capture.

Read-only: builds the FastAPI application in the test/app-factory builder with an
isolated temporary database (never production data) and dumps the declared route
surface (method, path, name, handler, response model, status code, tags) plus the
OpenAPI operation IDs for both builders.

Usage:
    python verification/v0.9.5-b/capture_route_inventory.py --out <json> --label <name>
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from app.api.main import create_app
from app.config import Settings


def _route_rows(app):
    rows = []
    for index, route in enumerate(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        declared_methods = sorted(m for m in methods if m not in {"HEAD", "OPTIONS"})
        handler = getattr(route, "endpoint", None)
        response_model = getattr(route, "response_model", None)
        status_code = getattr(route, "status_code", None)
        rows.append({
            "index": index,
            "path": path,
            "methods": declared_methods,
            "name": getattr(route, "name", None),
            "handler": f"{handler.__module__}.{handler.__name__}" if handler else None,
            "response_model": getattr(response_model, "__name__", None) if response_model is not None else None,
            "status_code": status_code if status_code is not None else 200,
            "tags": list(getattr(route, "tags", None) or []),
        })
    return rows


def _openapi_rows(spec):
    rows = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            rows.append({
                "path": path,
                "method": method.upper(),
                "operationId": operation.get("operationId"),
                "tags": operation.get("tags", []),
            })
    return rows


def _duplicates(rows):
    seen = {}
    for row in rows:
        for method in row["methods"]:
            seen.setdefault((row["path"], method), []).append(row["handler"])
    return [
        {"path": key[0], "method": key[1], "handlers": handlers}
        for key, handlers in seen.items()
        if len(handlers) > 1
    ]


def _first_health(app):
    for index, route in enumerate(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None) or set()
        if path == "/api/v1/system/health" and "GET" in methods:
            handler = getattr(route, "endpoint", None)
            return {
                "path": path,
                "index": index,
                "handler": f"{handler.__module__}.{handler.__name__}" if handler else None,
            }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture FastAPI route inventory.")
    parser.add_argument("--out", required=True, help="JSON output path.")
    parser.add_argument("--label", default="inventory", help="Inventory label.")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp_dir:
        settings = Settings(
            database_path=str(Path(tmp_dir) / "inventory.db"),
            llm_provider="local",
            deepseek_api_key=None,
            deepseek_base_url="https://example.invalid",
            deepseek_model="deepseek-test",
        )
        test_app = create_app(settings)
        prod_app = create_app()

        test_rows = _route_rows(test_app)
        prod_rows = _route_rows(prod_app)
        payload = {
            "label": args.label,
            "test_builder_routes": test_rows,
            "prod_created_routes": prod_rows,
            "test_builder_openapi": _openapi_rows(test_app.openapi()),
            "prod_created_openapi": _openapi_rows(prod_app.openapi()),
            "health_first_match_test_builder": _first_health(test_app),
            "health_first_match_prod_created": _first_health(prod_app),
            "test_builder_count": len(test_rows),
            "prod_created_count": len(prod_rows),
            "test_builder_duplicates": _duplicates(test_rows),
        }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    summary = {
        key: value
        for key, value in payload.items()
        if key not in {"test_builder_routes", "prod_created_routes",
                       "test_builder_openapi", "prod_created_openapi"}
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
