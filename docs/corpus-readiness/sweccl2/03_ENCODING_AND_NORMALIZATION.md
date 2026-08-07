# 03 — Encoding and Normalization

## Method

Per-file detection: ASCII strict, then UTF-8 strict, then GBK strict, then
charset_normalizer fallback. Strict decode + round-trip verification
(derived.encode(encoding) == original bytes). Detailed report:
`data/encoding_report.json`; per-file provenance: `data/derived_manifest.csv`.

## Results

| Metric | Value |
| --- | --- |
| Text files (.txt) | 17,703 |
| Decoded losslessly | 17,703 (100%) |
| NEEDS_REVIEW | 0 |
| ASCII | 17,600 |
| GBK | 101 |
| cp1250 (fallback) | 2 |
| Newlines | CRLF throughout (2 files without newlines); preserved as-is |

## Derived canonical layer

Location: `A:\[Linguistics Data] Corpus\SWECCL 2.0\PREPARED\utf8\` (mirrors the
source tree; outside git). Conversion is minimal: byte-for-byte content
preserved, only encoding changed to UTF-8; newlines untouched; no spelling,
grammar, punctuation, or content normalization of any kind.

## Special cases (documented, not repaired)

- WARG2730 / WARG4140 (LEMMA): decoded via cp1250 fallback (strict GBK failed on
  a byte sequence produced by a TreeTagger fragment). The files contain Chinese
  characters from the source essays processed by TreeTagger into tab-separated
  rows. Conversion is byte-lossless (round-trip verified); the Chinese fragment
  renders as mojibake under cp1250. These two files are flagged for manual
  review (`quality_issues.csv`).
- WARG2081 RAW/LEMMA: all-NUL files; derived copies are flagged
  `NEEDS_REVIEW`-equivalent (all-NUL, no text); excluded from usable text.

## Token-count note

Physical whitespace-split token totals (1,248,026) differ from the manual
(1,248,476, WordSmith Tools 5.0) by 0.04%; the difference is the counting
method, not content. Any future feature pipeline must define one token counter.
