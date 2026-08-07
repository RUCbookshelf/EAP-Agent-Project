# 07 — Corpus Composition

Data: `data/corpus_composition.csv`, `data/documentation_vs_physical.csv`.

## Usable written corpus (WECCL 2.0)

- 4,950 logical texts (4,950 raw, 4,949 usable raw; 4,949 usable lemma;
  4,950 usable tagged).
- Physical token total (whitespace split, header excluded): 1,248,026 vs
  manual 1,248,476 (difference 450, 0.04%, counting-method note).

All documented count dimensions match exactly (see 04). Notable distributions:

| Prompt | N | Prompt | N |
| --- | --- | --- | --- |
| ARG17 | 656 | ARG24 | 89 |
| ARG02 | 426 | ARG03 | 87 |
| ARG26 | 419 | ARG16 | 66 |
| ARG23 | 391 | ARG25 | 99 |
| ARG10 | 256 | ARG20 | 32 |
| ARG04 | 239 | ARG19 | 18 |
| ARG08 | 214 | ARG13 | 14 |
| ARG05 | 192 | EXP01 | 270 |
| ARG07 | 177 | ARG21 | 157 |
| ARG22 | 165 | ARG11 | 156 |
| ARG09 | 154 | ARG12 | 108 |
| ARG15 | 126 | ARG18 | 43 |
| ARG06 | 127 | ARG14 | 136 |
| ARG01 | 133 | | |

Extreme imbalances exist by design of the collection (ARG13 N=14, ARG19 N=18,
EXP01 is a single prompt with 270 texts) and must constrain reference-group
claims.

## SECCL 2.0 (inventory-level composition)

- Audio: 2,139 mp3 (TASK1/2/3 = 713 each; years 2003-2006; 6 groups/year).
- Transcripts: 2,852 (TASK1/2/3 713 each + TASK123 713; year counts 644/732/
  744/732 incl. merged texts).
- TEM8 component: absent from this physical copy (documented 916 files).

## Documentation-vs-physical status

- All N-count dimensions: MATCH.
- Token totals: documented 1,248,476 vs physical 1,248,026 (MISMATCH by
  method; 41 dimension cells differ by <=0.1%).
