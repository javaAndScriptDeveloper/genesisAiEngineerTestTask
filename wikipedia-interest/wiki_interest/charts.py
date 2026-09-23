"""Chart: per-million views per language, spike markers, dashed clipped trend."""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .run import RunResult, key  # noqa: E402

COLORS = ["#1f77b4", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b", "#e377c2", "#17becf"]


def render_chart(run: RunResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = len(run.topics)
    cols = 1 if n == 1 else 2
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(10.67, 6 if n == 1 else 4 * rows), dpi=150, squeeze=False)
    for ax, topic in zip(axes.flat, run.topics):
        _plot_topic(ax, run, topic)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    fig.suptitle(f"Wikipedia interest, views per million project views · {run.window.start}..{run.window.end} · agent=user",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _plot_topic(ax, run: RunResult, topic: str) -> None:
    x_labels = run.window.periods
    x = np.arange(len(x_labels))
    plotted = 0
    for i, lang in enumerate(run.langs):
        s = next(s for s in run.series if s.topic == topic and s.lang == lang)
        m = run.metrics.get(key(topic, lang))
        color = COLORS[i % len(COLORS)]
        if s.status != "ok" or m is None:
            ax.plot([], [], color=color, label=f"{lang}: {s.status.upper()}")
            continue
        y = np.asarray(s.per_million)
        ax.plot(x, y, color=color, lw=1.6, label=f"{lang}: {s.title} ({m.confidence})")
        spikes = np.zeros(len(y), dtype=bool)
        for p in m.spike_periods:
            if p in x_labels:
                spikes[x_labels.index(p)] = True
        if spikes.any():
            ax.scatter(x[spikes], y[spikes], color=color, marker="^", s=40, zorder=3)
        fit_x = x[~spikes]
        if m.growth_clipped_pct_per_year is not None and len(fit_x) >= 3:
            slope, intercept = np.polyfit(fit_x, np.log1p(y)[~spikes], 1)
            ax.plot(x, np.expm1(intercept + slope * x), color=color, lw=1, ls="--", alpha=0.7)
        plotted += 1
    ax.set_title(topic, fontsize=10)
    ax.set_ylabel("views per million")
    step = max(1, len(x_labels) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([x_labels[i] for i in range(0, len(x_labels), step)], rotation=45, ha="right", fontsize=7)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="upper left")
    if plotted == 0:
        ax.text(0.5, 0.5, "no usable data", ha="center", va="center", transform=ax.transAxes)
