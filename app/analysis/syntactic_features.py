from __future__ import annotations


FINITE_TAGS = {"VBD", "VBP", "VBZ", "MD"}
SUBORDINATE_DEPS = {"advcl", "ccomp", "xcomp", "acl", "relcl", "csubj"}
COORDINATION_DEPS = {"conj", "cc"}


def _tree_depth(token) -> int:
    depth = 0
    seen = set()
    current = token
    while current.head is not current and current.i not in seen:
        seen.add(current.i)
        depth += 1
        current = current.head
    return depth


def extract_syntactic_features(doc, *, long_sentence_threshold: int = 30) -> dict:
    sentences = list(doc.sents)
    sentence_details: list[dict] = []
    finite = []
    subordinate = []
    coordination = []
    clause_like = []
    depths = []
    for sid, sent in enumerate(sentences, 1):
        lexical = [token for token in sent if not token.is_space and not token.is_punct]
        depth = max((_tree_depth(token) for token in sent), default=0)
        depths.append(depth)
        sentence_details.append({
            "sentence_id": sid, "text": sent.text, "start_offset": sent.start_char,
            "end_offset": sent.end_char, "token_count": len(lexical), "dependency_tree_depth": depth,
            "long_sentence_candidate": len(lexical) >= long_sentence_threshold,
        })
        for token in sent:
            evidence = {"sentence_id": sid, "text": token.text, "start_offset": token.idx, "end_offset": token.idx + len(token.text), "dependency": token.dep_}
            if token.tag_ in FINITE_TAGS or "Fin" in token.morph.get("VerbForm"):
                finite.append(evidence)
            if token.dep_ in SUBORDINATE_DEPS:
                subordinate.append(evidence)
                clause_like.append(evidence)
            if token.dep_ in COORDINATION_DEPS:
                coordination.append(evidence)
            if token.dep_ == "ROOT" and token.pos_ in {"VERB", "AUX"}:
                clause_like.append(evidence)
    noun_phrases = []
    try:
        for chunk in doc.noun_chunks:
            noun_phrases.append({
                "text": chunk.text, "token_count": len(chunk), "start_offset": chunk.start_char,
                "end_offset": chunk.end_char,
            })
    except (ValueError, NotImplementedError):
        noun_phrases = []
    return {
        "sentences": sentence_details,
        "sentence_length_distribution": [item["token_count"] for item in sentence_details],
        "finite_verb_candidates": finite,
        "subordinate_clause_candidates": subordinate,
        "coordination_candidates": coordination,
        "dependency_tree_depths": depths,
        "mean_dependency_tree_depth": round(sum(depths) / len(depths), 3) if depths else 0.0,
        "noun_phrase_candidates": noun_phrases,
        "mean_noun_phrase_length": round(sum(item["token_count"] for item in noun_phrases) / len(noun_phrases), 3) if noun_phrases else 0.0,
        "long_sentence_candidates": [item for item in sentence_details if item["long_sentence_candidate"]],
        "clause_like_unit_candidates": clause_like,
        "limitations": [
            "Parser-derived structures are automatic candidates and may be inaccurate for learner language.",
            "Sentence length is not treated as complexity or quality; this is not full T-unit analysis.",
        ],
    }

