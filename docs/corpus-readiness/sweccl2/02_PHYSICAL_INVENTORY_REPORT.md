# 02 — Physical Inventory Report

## Method

Deterministic walk of the corpus root (sorted traversal, chunked SHA-256,
fixed schema). Full inventory: `data/physical_inventory.csv`.
Discovery-time snapshot (includes the manual PDF):
`data/physical_inventory_discovery_snapshot.csv`.

## Coverage

- 19,858 files, 100% hashed, 0 read errors.
- Physical status: 19,858/19,858 `ok`.
- Encoding status (current inventory): 17,601 ASCII, 101 GBK, 2 cp1250,
  2,153 binary/needs-review (all non-text binaries: 2,139 mp3, 8 exe,
  1 pdf [TOOLS User Guide], 2 doc, 1 avi, 1 sav, 1 xls), plus the UTF-8
  report file copied into the root during preparation.
- The second PDF (the manual) was present at discovery and is recorded in
  `physical_inventory_discovery_snapshot.csv` (15,126,818 bytes); it was
  relocated out of the root afterwards.

## Documentation-vs-physical file counts

| Component | Documentation | Physical | Status |
| --- | --- | --- | --- |
| WECCL RAW/LEMMA/TAGGED | 4,950 each | 4,950 each | MATCH |
| SECCL AUDIO (mp3) | 2,139 | 2,139 | MATCH |
| SECCL TEXTS (transcripts) | 2,852 | 2,852 | MATCH |
| SECCL TASK123 merged texts | 713 | 713 | MATCH |
| TEM8 folder | 916 files (documented) | 0 | UNEXPLAINED ABSENCE |
| TOOLS | tools described in manual | 13 files incl. exp.sav/exp.xls | PRESENT |

## Notes

- File counts per SECCL year (TEXTS incl. TASK123): 2003 = 644, 2004 = 732,
  2005 = 744, 2006 = 732; task-only counts (TASK1/2/3) are 483/549/558/549 and
  match the manual tables.
- The manual PDF (documentation) was present at discovery and moved out of the
  root during preparation; hash preserved in the snapshot.
