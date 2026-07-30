# Lexical Diversity v0.8

Normalization uses lowercase alphabetic spaCy surface tokens; punctuation and numbers are excluded. This policy and its unit version travel with every result.

- TTR: unique normalized tokens divided by normalized tokens.
- MATTR: mean TTR across overlapping 50-token windows; shorter input is unavailable under the existing protocol.
- MTLD: mean forward/reverse factor length at threshold 0.72, including proportional partial factors. Minimum input is 10 tokens.
- HD-D: expected type contribution under a hypergeometric sample of 42, divided by 42. Input shorter than 42 tokens is unavailable, never zero.

MTLD and HD-D persist numerator/denominator where applicable, factor or per-type intermediate values, configured parameters, token counts, status, confidence, and limitations. Exact version/unit compatibility is required for trajectories.
