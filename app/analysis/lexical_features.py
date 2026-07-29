from __future__ import annotations

from collections import Counter
import re


CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}


def moving_average_ttr(lemmas: list[str], window: int) -> tuple[float | None, str]:
    if len(lemmas) < window:
        return None, "insufficient_data"
    values = [len(set(lemmas[i:i + window])) / window for i in range(len(lemmas) - window + 1)]
    return round(sum(values) / len(values), 4), "available"


def extract_lexical_features(doc, prompt_doc, *, mattr_window: int = 50, local_window: int = 30) -> dict:
    lexical = [token for token in doc if token.is_alpha]
    surface_tokens = [token.text.lower() for token in lexical]
    lemmas = [(token.lemma_ or token.text).lower() for token in lexical]
    content = [token for token in lexical if token.pos_ in CONTENT_POS]
    content_lemmas = [(token.lemma_ or token.text).lower() for token in content]
    prompt_keywords = sorted({
        (token.lemma_ or token.text).lower() for token in prompt_doc
        if token.is_alpha and token.pos_ in CONTENT_POS and not token.is_stop
    })
    counts = Counter(content_lemmas)
    paragraph_spans = [(m.start(), m.end()) for m in re.finditer(r"\S(?:.*?\S)?(?=(?:\r?\n\s*){2,}|\Z)", doc.text, re.DOTALL)]
    repeated_details: list[dict] = []
    for lemma, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if count < 3 or len(lemma) < 3:
            continue
        occurrences = []
        indexes = []
        for token in content:
            if (token.lemma_ or token.text).lower() == lemma:
                indexes.append(token.i)
                occurrences.append({
                    "sentence_id": next((i for i, sent in enumerate(doc.sents, 1) if sent.start <= token.i < sent.end), None),
                    "paragraph_id": next((i for i, (start, end) in enumerate(paragraph_spans, 1) if start <= token.idx < end), None),
                    "start_offset": token.idx, "end_offset": token.idx + len(token.text), "surface": token.text,
                })
        local_cluster = any(sum(1 for j in indexes if i <= j < i + local_window) >= 3 for i in indexes)
        is_keyword = lemma in prompt_keywords
        paragraph_ids = sorted({item["paragraph_id"] for item in occurrences if item["paragraph_id"] is not None})
        sentence_ids = sorted({item["sentence_id"] for item in occurrences if item["sentence_id"] is not None})
        pos_values = sorted({token.pos_ for token in content if (token.lemma_ or token.text).lower() == lemma})
        necessary_term = bool(len(paragraph_ids) >= 2 and any(pos in {"NOUN", "PROPN"} for pos in pos_values))
        repeated_details.append({
            "lemma": lemma, "count": count, "is_prompt_keyword": is_keyword,
            "is_necessary_task_term_candidate": necessary_term,
            "necessary_term_rule_version": "necessary-task-term-v0.6.1",
            "local_cluster_detected": local_cluster,
            "diagnostic_weight": "low" if (is_keyword or necessary_term) and not local_cluster else "medium",
            "density": round(count / max(1, len(content_lemmas)), 4), "occurrences": occurrences,
            "sentence_ids": sentence_ids, "sentence_distance": (max(sentence_ids) - min(sentence_ids)) if sentence_ids else None,
            "paragraph_distribution": paragraph_ids, "pos": pos_values,
            "limitations": ["Necessary-task-term detection is a conservative morphology/distribution heuristic, not semantic confirmation."],
        })
    mattr, mattr_status = moving_average_ttr(surface_tokens, mattr_window)
    pos_distribution = dict(Counter(token.pos_ for token in lexical))
    repetition_numerator = sum(item["count"] for item in repeated_details)
    token_protocol = {
        "token_definition": "alphabetic_spacy_tokens", "normalization": "lowercase_surface",
        "lemma_used": False, "punctuation_excluded": True, "numbers_excluded": True,
        "token_count_used": len(surface_tokens), "type_count_used": len(set(surface_tokens)),
    }
    return {
        "lemma_frequencies": dict(Counter(lemmas).most_common()),
        "lemma_frequency_protocol": {**token_protocol, "normalization": "lowercase_lemma", "lemma_used": True},
        "content_word_frequencies": dict(counts.most_common()),
        "content_token_count": len(content), "function_token_count": len(lexical) - len(content),
        "prompt_keywords": prompt_keywords, "repeated_content_word_details": repeated_details,
        "repeated_content_words": {item["lemma"]: item["count"] for item in repeated_details},
        "repetition_density": round(repetition_numerator / max(1, len(content_lemmas)), 4),
        "repetition_density_numerator": repetition_numerator,
        "repetition_density_denominator": len(content_lemmas),
        "repetition_protocol": {
            "numerator": "occurrences_of_content_lemma_candidates_with_count_at_least_3",
            "denominator": "content_token_count", "local_window_tokens": local_window,
        },
        "pos_distribution": pos_distribution,
        "lexical_density": round(len(content) / len(lexical), 4) if lexical else 0.0,
        "lexical_density_protocol": {**token_protocol, "content_pos": sorted(CONTENT_POS), "content_token_count": len(content)},
        "mattr": mattr, "mattr_status": mattr_status, "mattr_window": mattr_window,
        "mattr_protocol": {**token_protocol, "window_size": mattr_window,
                           "effective_windows": max(0, len(surface_tokens) - mattr_window + 1),
                           "minimum_text_length": mattr_window},
        "type_token_ratio": round(len(set(surface_tokens)) / len(surface_tokens), 4) if surface_tokens else 0.0,
        "type_token_ratio_protocol": token_protocol,
    }
