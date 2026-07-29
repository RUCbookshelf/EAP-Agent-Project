from __future__ import annotations

import importlib.metadata
import argparse
import json


def status() -> dict:
    result = {
        "active_analyzer": "spacy", "spacy_installed": False,
        "spacy_version": None, "model_name": "en_core_web_sm",
        "model_installed": False, "model_version": None,
        "fallback_available": True,
    }
    try:
        import spacy
        result["spacy_installed"] = True
        result["spacy_version"] = spacy.__version__
        spacy.load("en_core_web_sm")
        result["model_installed"] = True
        result["model_version"] = importlib.metadata.version("en_core_web_sm")
    except Exception as exc:
        result["fallback_reason"] = f"{type(exc).__name__}: {str(exc)[:180]}"
    result["status"] = "PASS" if result["model_installed"] else "FALLBACK_AVAILABLE"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-model", action="store_true")
    args = parser.parse_args()
    result = status()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    if args.require_model and not result["model_installed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
