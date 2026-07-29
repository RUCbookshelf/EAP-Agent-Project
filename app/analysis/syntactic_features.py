from __future__ import annotations

import re


FINITE_TAGS = {"VBD", "VBP", "VBZ", "MD"}
SUBORDINATE_DEPS = {"advcl", "ccomp", "xcomp", "acl", "relcl", "csubj"}


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
    paragraph_spans = [(m.start(), m.end()) for m in re.finditer(r"\S(?:.*?\S)?(?=(?:\r?\n\s*){2,}|\Z)", doc.text, re.DOTALL)]
    sentence_details: list[dict] = []
    finite = []
    subordinate = []
    coordination = []
    coordinators = []
    conjuncts = []
    coordinated_heads: set[tuple[int, int]] = set()
    subordinate_by_dependency = {dep: [] for dep in sorted(SUBORDINATE_DEPS)}
    clause_like = []
    depths = []
    for sid, sent in enumerate(sentences, 1):
        lexical = [token for token in sent if not token.is_space and not token.is_punct]
        depth = max((_tree_depth(token) for token in sent), default=0)
        depths.append(depth)
        sentence_details.append({
            "sentence_id": sid, "text": sent.text, "start_offset": sent.start_char,
            "end_offset": sent.end_char, "token_count": len(lexical), "dependency_tree_depth": depth,
            "paragraph_id": next((i for i, (start, end) in enumerate(paragraph_spans, 1) if start <= sent.start_char < end), None),
            "long_sentence_candidate": len(lexical) >= long_sentence_threshold,
        })
        for token in sent:
            evidence = {"sentence_id": sid, "text": token.text, "start_offset": token.idx, "end_offset": token.idx + len(token.text), "dependency": token.dep_}
            if token.tag_ in FINITE_TAGS or "Fin" in token.morph.get("VerbForm"):
                finite.append({
                    **evidence, "pos": token.pos_, "tag": token.tag_,
                    "verb_form": list(token.morph.get("VerbForm")),
                    "is_auxiliary": token.pos_ == "AUX",
                    "counting_rule": "one candidate per token with finite morphology or VBD/VBP/VBZ/MD tag",
                })
            if token.dep_ in SUBORDINATE_DEPS:
                subordinate.append(evidence)
                subordinate_by_dependency[token.dep_].append(evidence)
                clause_like.append(evidence)
            if token.dep_ == "cc":
                coordinators.append(evidence)
                coordination.append(evidence)
            if token.dep_ == "conj":
                conjuncts.append(evidence)
                coordination.append(evidence)
                coordinated_heads.add((sid, token.head.i))
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
        "clause_like_dependency_candidates_by_type": subordinate_by_dependency,
        "coordination_candidates": coordination,
        "coordinator_tokens": coordinators,
        "conjunct_dependencies": conjuncts,
        "coordinated_structure_candidates": [
            {"sentence_id": sid, "head_token_index": head_index}
            for sid, head_index in sorted(coordinated_heads)
        ],
        "dependency_tree_depths": depths,
        "mean_dependency_tree_depth": round(sum(depths) / len(depths), 3) if depths else 0.0,
        "noun_phrase_candidates": noun_phrases,
        "mean_noun_phrase_length": round(sum(item["token_count"] for item in noun_phrases) / len(noun_phrases), 3) if noun_phrases else 0.0,
        "long_sentence_candidates": [item for item in sentence_details if item["long_sentence_candidate"]],
        "clause_like_unit_candidates": clause_like,
        "limitations": [
            "Parser-derived structures are automatic candidates and may be inaccurate for learner language.",
            "Coordinator tokens, conjunct dependencies and coordinated-structure candidates are separate counts and must not be summed as confirmed structures.",
            "advcl/relcl/ccomp/xcomp/csubj/acl are reported separately and are not asserted to be confirmed subordinate clauses.",
            "Finite verbs are token candidates based on morphology/tags; finite AUX is counted while participial main verbs are not independently treated as finite.",
            "Sentence length is not treated as complexity or quality; this is not full T-unit analysis.",
        ],
    }
