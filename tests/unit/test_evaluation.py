"""
Unit tests for DocIntel Evaluation Platform.
Verifies CER and WER calculations, field F1 scores, Seaborn chart creation, and Markdown report generation.
"""

from pathlib import Path

from docintel.evaluation.metrics_text import compute_cer, compute_field_f1, compute_wer
from docintel.evaluation.reports import generate_evaluation_report


def test_compute_cer_wer_perfect_match():
    """Verify identical text produces 0.0 error rate."""
    ref = "Open Doc Intelligence Grounded OCR"
    hyp = "Open Doc Intelligence Grounded OCR"
    assert compute_cer(ref, hyp) == 0.0
    assert compute_wer(ref, hyp) == 0.0


def test_compute_cer_with_errors():
    """Verify Character Error Rate calculation on intentional typos."""
    ref = "Invoice Number 12345"
    hyp = "Invoce Numbr 12345"  # Two deletions
    cer = compute_cer(ref, hyp)
    assert 0.05 < cer < 0.20


def test_compute_field_f1():
    """Verify field-level entity extraction F1 precision and recall."""
    expected = {
        "title": "Quarterly Report",
        "vendor": "Acme Corp",
        "total": "$5,000",
        "date": "2026-10-15",
    }
    predicted = {
        "title": "Quarterly Report",
        "vendor": "Acme Corp",
        "total": "$5,000",
        "date": "2026-10-14",  # Discrepancy
    }
    scores = compute_field_f1(expected, predicted)
    assert scores["matches"] == 3
    assert scores["precision"] == 0.75
    assert scores["recall"] == 0.75
    assert scores["f1"] == 0.75


def test_generate_evaluation_report(tmp_path: Path):
    """Verify report generation produces markdown and high-resolution chart files."""
    report_file = generate_evaluation_report(eval_dir=tmp_path)
    assert report_file.is_file()
    assert report_file.name == "evaluation_report.md"

    # Verify generated charts exist
    assert (tmp_path / "cer_wer_distribution.png").is_file()
    assert (tmp_path / "field_f1_scores.png").is_file()
    assert (tmp_path / "latency_vs_accuracy.png").is_file()

    content = report_file.read_text(encoding="utf-8")
    assert "Open Doc Intelligence - Benchmark & Evaluation Report" in content
    assert "Character Error Rate (CER)" in content
