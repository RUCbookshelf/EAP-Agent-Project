# 01 — Corpus Resource Registration

## Implementation

`app/corpus/resource.py` provides the minimum architecture-approved corpus
resource registration (D-24 boundary). It consumes the existing preparation
artifacts directly - `corpus_version.json` plus the 11 machine-readable
manifest files - and introduces no second corpus manifest and no database
persistence.

## Registered identity

| Field | Value |
| --- | --- |
| corpus_package_id | sweccl2-weccl20-v0.1.0 |
| source_corpus | SWECCL 2.0 (ISBN 978-7-5600-8015-4) |
| preparation_version | 0.1.0 |
| manifest_hash | 0d8940ff84613807c11c0e492c61fb8d39fc1152a386061f9711a41487659eb9 |
| usable_logical_text_count | 4,950 |
| usable_variants | raw 4,949 / lemma 4,949 / tagged 4,950 |
| license_status | PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW |

## Verification behavior

- On load, the canonical composite hash is recomputed over the 11 manifest
  files (fixed order, name + NUL + content + NUL) and compared to the
  recorded hash. Mismatch raises CorpusResourceError with expected/computed
  values.
- Package id mismatch, missing corpus_version.json, missing manifest files,
  prepared-root absence, variant directory shortfall, and manifest row-count
  mismatch all fail safely with explicit errors.
- The descriptor is immutable (frozen dataclass); provenance is exposed
  programmatically via `descriptor.provenance`.
- `get_corpus_resource()` provides a cached accessor for the internal
  boundary; `load_corpus_resource()` performs fresh verification.

## Coverage of WU1 gate

Registered resource, manifest verified, package version verified,
deterministic load succeeds, invalid hash/version/missing root fail safely -
all covered by tests/corpus/test_resource.py (8 tests).
