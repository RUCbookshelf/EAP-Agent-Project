from __future__ import annotations

from collections import Counter


CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}


def moving_average_ttr(lemmas: list[str], window: int) -> tuple[float | None, str]:
    if len(lemmas) < window:
        return None, "insufficient_data"
    values = [len(set(lemmas[i:i + window])) / window for i in range(len(lemmas) - window + 1)]
    return round(sum(values) / len(values), 4), "available"


def extract_lexical_features(doc, prompt_doc, *, mattr_window: int = 50, local_window: int = 30) -> dict:
    lexical = [token for token in doc if token.is_alpha]
    lemmas = [(token.lemma_ or token.text).lower() for token in lexical]
    content = [token for token in lexical if token.pos_ in CONTENT_POS]
    content_lemmas = [(token.lemma_ or token.text).lower() for token in content]
    prompt_keywords = sorted({
        (token.lemma_ or token.text).lower() for token in prompt_doc
        if token.is_alpha and token.pos_ in CONTENT_POS and not token.is_stop
    })
    counts = Counter(content_lemmas)
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
                    "start_offset": token.idx, "end_offset": token.idx + len(token.text), "surface": token.text,
                })
        local_cluster = any(sum(1 for j in indexes if i <= j < i + local_window) >= 3 for i in indexes)
        is_keyword = lemma in prompt_keywords
        repeated_details.append({
            "lemma": lemma, "count": count, "is_prompt_keyword": is_keyword,
            "local_cluster_detected": local_cluster,
            "diagnostic_weight": "low" if is_keyword and not local_cluster else "medium",
            "density": round(count / max(1, len(content_lemmas)), 4), "occurrences": occurrences,
            "pos": sorted({token.pos_ for token in content if (token.lemma_ or token.text).lower() == lemma}),
        })
    mattr, mattr_status = moving_average_ttr(lemmas, mattr_window)
    pos_distribution = dict(Counter(token.pos_ for token in lexical))
    return {
        "lemma_frequencies": dict(Counter(lemmas).most_common()),
        "content_word_frequencies": dict(counts.most_common()),
        "content_token_count": len(content), "function_token_count": len(lexical) - len(content),
        "prompt_keywords": prompt_keywords, "repeated_content_word_details": repeated_details,
        "repeated_content_words": {item["lemma"]: item["count"] for item in repeated_details},
        "repetition_density": round(sum(item["count"] for item in repeated_details) / max(1, len(content_lemmas)), 4),
        "pos_distribution": pos_distribution,
        "lexical_density": round(len(content) / len(lexical), 4) if lexical else 0.0,
        "mattr": mattr, "mattr_status": mattr_status, "mattr_window": mattr_window,
        "type_token_ratio": round(len(set(lemmas)) / len(lemmas), 3) if lemmas else 0.0,
    }

