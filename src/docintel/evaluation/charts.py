"""
Publication-Quality Seaborn & Matplotlib Visualization Engine.
Generates 300+ DPI statistical charts for Character/Word Error Rates (CER/WER),
field-level entity F1 benchmarks, and model latency/accuracy trade-offs.
"""

from pathlib import Path
from typing import Any

try:
    import matplotlib
    matplotlib.use("Agg")  # Headless backend
    import matplotlib.pyplot as plt
    import pandas as pd
    import seaborn as sns
    PLT_AVAILABLE = True
except ImportError:
    PLT_AVAILABLE = False


def _set_publication_style():
    """Apply clean, high-contrast, modern aesthetic styles for benchmark figures."""
    if not PLT_AVAILABLE:
        return
    sns.set_theme(style="whitegrid", font="sans-serif")
    plt.rcParams.update({
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.titlesize": 14,
        "figure.dpi": 300,
    })


def generate_cer_wer_boxplot(data: list[dict[str, Any]], output_path: Path | str) -> Path:
    """
    Generate a boxplot comparing Character Error Rate (CER) and Word Error Rate (WER) across models.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not PLT_AVAILABLE or not data:
        # Fallback text representation if matplotlib is not available
        out.write_text("CER/WER Evaluation Boxplot Placeholder (Matplotlib not available)", encoding="utf-8")
        return out

    _set_publication_style()
    df = pd.DataFrame(data)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    palette = {"cer": "#ff7644", "wer": "#3b82f6"}

    # Melt to long form
    if "metric" not in df.columns and "cer" in df.columns and "wer" in df.columns:
        df_melt = pd.melt(df, id_vars=["engine"], value_vars=["cer", "wer"], var_name="Metric", value_name="Error Rate")
    else:
        df_melt = df

    sns.boxplot(
        data=df_melt,
        x="engine",
        y="Error Rate",
        hue="Metric",
        palette=palette,
        ax=ax,
        width=0.55,
        fliersize=3,
    )

    ax.set_title("Open Doc Intelligence - CER & WER Error Rate Distribution", weight="bold", pad=12)
    ax.set_xlabel("Engine / Architecture", weight="bold")
    ax.set_ylabel("Error Rate (Lower is Better)", weight="bold")
    ax.set_ylim(-0.01, max(0.25, df_melt["Error Rate"].max() + 0.05))
    ax.legend(title="Metric (CER / WER)", frameon=True, facecolor="#f8fafc")

    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_field_f1_barchart(metrics: dict[str, float], output_path: Path | str) -> Path:
    """
    Generate horizontal bar chart for field-level extraction F1 scores across structural categories.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not PLT_AVAILABLE or not metrics:
        out.write_text("Field F1 Bar Chart Placeholder", encoding="utf-8")
        return out

    _set_publication_style()
    categories = list(metrics.keys())
    scores = [v * 100 for v in metrics.values()]

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=300)
    colors = ["#ff7644", "#8b5cf6", "#3b82f6", "#00c9b7", "#f59e0b"][:len(categories)]

    bars = ax.barh(categories, scores, color=colors, height=0.55, edgecolor="none")
    ax.set_xlim(0, 105)
    ax.set_xlabel("F1 Accuracy Score (%)", weight="bold")
    ax.set_title("Field-Level Extraction F1 Across Document Layout Entities", weight="bold", pad=12)

    # Annotate bar values
    for bar in bars:
        w = bar.get_width()
        ax.text(w + 1.2, bar.get_y() + bar.get_height() / 2, f"{w:.1f}%", va="center", weight="bold", fontsize=10, color="#1e293b")

    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out


def generate_throughput_scatter(benchmarks: list[dict[str, Any]], output_path: Path | str) -> Path:
    """
    Generate scatter plot comparing Inference Latency (sec) vs. Accuracy (%) with VRAM dot sizes.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not PLT_AVAILABLE or not benchmarks:
        out.write_text("Throughput Scatter Placeholder", encoding="utf-8")
        return out

    _set_publication_style()
    df = pd.DataFrame(benchmarks)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=300)
    scatter = ax.scatter(
        df["latency_sec"],
        df["accuracy_percent"],
        s=df["vram_mb"] / 4,
        c=["#3b82f6", "#ff7644", "#00c9b7", "#8b5cf6"][:len(df)],
        alpha=0.85,
        edgecolors="#ffffff",
        linewidth=1.5,
    )

    for _, row in df.iterrows():
        ax.annotate(
            f" {row['engine']}\n ({row['vram_mb']}MB)",
            (row["latency_sec"], row["accuracy_percent"]),
            fontsize=9.5,
            weight="bold",
            color="#1e293b",
        )

    ax.set_title("Inference Latency vs. Recognition Accuracy (Dot Size = Peak VRAM)", weight="bold", pad=12)
    ax.set_xlabel("Processing Latency per Page (Seconds)", weight="bold")
    ax.set_ylabel("Recognition Accuracy (%)", weight="bold")
    ax.set_ylim(85, 101)

    plt.tight_layout()
    plt.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out
