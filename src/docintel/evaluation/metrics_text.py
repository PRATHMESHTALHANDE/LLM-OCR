"""
Standardized Text Extraction Metrics Engine.
Computes Character Error Rate (CER) and Word Error Rate (WER) using jiwer,
along with field-level Precision, Recall, and F1 scores for structured document understanding.
"""

import re
from typing import Any

try:
    import jiwer
    JIWER_AVAILABLE = True
except ImportError:
    JIWER_AVAILABLE = False


def normalize_text_for_eval(text: str, remove_punct: bool = False, lower: bool = True) -> str:
    """Normalize text for consistent benchmark scoring."""
    if not text:
        return ""
    res = text.strip()
    if lower:
        res = res.lower()
    if remove_punct:
        res = re.sub(r'[^\w\s]', '', res)
    # Collapse multiple whitespaces
    res = re.sub(r'\s+', ' ', res)
    return res


def _levenshtein_distance(s1: list[str] | str, s2: list[str] | str) -> int:
    """Pure-Python Levenshtein distance matrix computation."""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    return dp[m][n]


def compute_cer(reference: str, hypothesis: str, normalize: bool = True) -> float:
    """
    Compute Character Error Rate (CER) between ground truth reference and predicted hypothesis.
    CER = (Substitutions + Deletions + Insertions) / Total Reference Characters.
    """
    ref = normalize_text_for_eval(reference) if normalize else reference
    hyp = normalize_text_for_eval(hypothesis) if normalize else hypothesis

    if not ref:
        return 0.0 if not hyp else 1.0

    if JIWER_AVAILABLE:
        try:
            return round(float(jiwer.cer(ref, hyp)), 4)
        except Exception:
            pass

    # Pure Python Levenshtein fallback
    distance = _levenshtein_distance(ref, hyp)
    return round(float(distance / len(ref)), 4)


def compute_wer(reference: str, hypothesis: str, normalize: bool = True) -> float:
    """
    Compute Word Error Rate (WER) between ground truth reference and predicted hypothesis.
    WER = (Word Substitutions + Deletions + Insertions) / Total Reference Words.
    """
    ref = normalize_text_for_eval(reference) if normalize else reference
    hyp = normalize_text_for_eval(hypothesis) if normalize else hypothesis

    if not ref:
        return 0.0 if not hyp else 1.0

    if JIWER_AVAILABLE:
        try:
            return round(float(jiwer.wer(ref, hyp)), 4)
        except Exception:
            pass

    ref_words = ref.split()
    hyp_words = hyp.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    distance = _levenshtein_distance(ref_words, hyp_words)
    return round(float(distance / len(ref_words)), 4)


def compute_field_f1(expected: dict[str, Any], predicted: dict[str, Any]) -> dict[str, float]:
    """
    Compute entity field-level Precision, Recall, and F1 score for structured key-value extraction.
    """
    if not expected:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "matches": 0, "total_expected": 0}

    true_positives = 0
    total_predicted = len(predicted)
    total_expected = len(expected)

    for k, expected_val in expected.items():
        if k in predicted:
            exp_norm = normalize_text_for_eval(str(expected_val))
            pred_norm = normalize_text_for_eval(str(predicted[k]))
            if exp_norm == pred_norm or (exp_norm in pred_norm or pred_norm in exp_norm):
                true_positives += 1

    precision = round(true_positives / total_predicted, 4) if total_predicted > 0 else 0.0
    recall = round(true_positives / total_expected, 4) if total_expected > 0 else 0.0
    f1 = round((2 * precision * recall) / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matches": true_positives,
        "total_expected": total_expected,
        "total_predicted": total_predicted,
    }
