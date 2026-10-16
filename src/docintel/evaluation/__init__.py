"""
Open Doc Intelligence - Evaluation Platform Package
Provides standardized CER/WER metrics via jiwer, publication-grade Seaborn charts, and automated markdown reports.
"""

from docintel.evaluation.charts import generate_cer_wer_boxplot, generate_field_f1_barchart, generate_throughput_scatter
from docintel.evaluation.metrics_text import compute_cer, compute_field_f1, compute_wer
from docintel.evaluation.reports import generate_evaluation_report

__all__ = [
    "compute_cer",
    "compute_wer",
    "compute_field_f1",
    "generate_cer_wer_boxplot",
    "generate_field_f1_barchart",
    "generate_throughput_scatter",
    "generate_evaluation_report",
]
