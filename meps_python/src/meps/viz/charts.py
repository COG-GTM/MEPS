"""Visualization utilities for MEPS analysis results.

Ports the ggplot_example.R visualization patterns using matplotlib and plotly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import polars as pl


def grouped_bar_chart(
    data: pl.DataFrame | dict[str, list[float]],
    x: str | list[str] = "category",
    y: str | list[str] = "value",
    group: Optional[str | list[str]] = None,
    title: str = "",
    colors: Optional[list[str]] = None,
    ylabel: str = "Percentage",
    xlabel: str = "",
    show_labels: bool = True,
    label_format: str = "{:.0f}",
    figsize: tuple[int, int] = (10, 6),
    save_path: Optional[str] = None,
    use_plotly: bool = False,
) -> object:
    """Create a grouped bar chart matching the ggplot_example.R style.

    Supports both matplotlib (static) and plotly (interactive) output.

    Args:
        data: Either a polars DataFrame or dict of {series_name: values}.
        x: Column name(s) for x-axis categories.
        y: Column name(s) for y-axis values.
        group: Column name for grouping (if data is a DataFrame).
        title: Chart title.
        colors: Custom colors for groups. Defaults to MEPS palette.
        ylabel: Y-axis label.
        xlabel: X-axis label.
        show_labels: Whether to show data labels on bars.
        label_format: Format string for data labels.
        figsize: Figure size (width, height) in inches.
        save_path: If provided, save the chart to this path.
        use_plotly: If True, use plotly instead of matplotlib.

    Returns:
        matplotlib Figure or plotly Figure object.
    """
    # Default MEPS colors (matching ggplot_example.R)
    if colors is None:
        colors = [
            "rgb(0,115,189)",      # blue
            "rgb(255,197,0)",      # yellow
            "rgb(99,16,99)",       # magenta
        ]

    if use_plotly:
        return _plotly_grouped_bar(data, x, y, group, title, colors, ylabel, xlabel,
                                   show_labels, label_format, save_path)
    else:
        return _matplotlib_grouped_bar(data, x, y, group, title, colors, ylabel, xlabel,
                                        show_labels, label_format, figsize, save_path)


def _parse_rgb(color_str: str) -> tuple[float, ...]:
    """Parse 'rgb(r,g,b)' string to matplotlib-compatible tuple."""
    if color_str.startswith("rgb(") and color_str.endswith(")"):
        parts = color_str[4:-1].split(",")
        return tuple(int(p.strip()) / 255.0 for p in parts)
    return (0.0, 0.0, 0.0)


def _matplotlib_grouped_bar(data, x, y, group, title, colors, ylabel, xlabel,
                             show_labels, label_format, figsize, save_path):
    """Create grouped bar chart using matplotlib."""
    import matplotlib.pyplot as plt

    # Convert data to matrix format
    if isinstance(data, dict):
        categories = list(data.keys()) if isinstance(x, str) else x
        if isinstance(y, list):
            matrix = np.array([data[k] for k in categories])
            group_labels = y
        else:
            matrix = np.array(list(data.values()))
            group_labels = list(data.keys())
    elif isinstance(data, pl.DataFrame):
        if group and group in data.columns:
            groups = data[group].unique().sort().to_list()
            cats = data[x].unique().sort().to_list() if isinstance(x, str) else x
            matrix = np.zeros((len(cats), len(groups)))
            for i, cat in enumerate(cats):
                for j, grp in enumerate(groups):
                    val = data.filter((pl.col(x) == cat) & (pl.col(group) == grp))
                    if val.height > 0:
                        matrix[i, j] = val[y if isinstance(y, str) else y[0]][0]
            categories = [str(c) for c in cats]
            group_labels = [str(g) for g in groups]
        else:
            categories = data[x].to_list() if isinstance(x, str) else x
            if isinstance(y, list):
                matrix = np.column_stack([data[col].to_numpy() for col in y])
                group_labels = y
            else:
                matrix = data[y].to_numpy().reshape(-1, 1)
                group_labels = [y]
    else:
        raise TypeError(f"data must be dict or polars DataFrame, got {type(data)}")

    n_cats = matrix.shape[0]
    n_groups = matrix.shape[1] if matrix.ndim > 1 else 1
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)

    mpl_colors = [_parse_rgb(c) if c.startswith("rgb") else c for c in colors[:n_groups]]

    fig, ax = plt.subplots(figsize=figsize)
    bar_width = 0.8 / n_groups
    x_pos = np.arange(n_cats)

    for j in range(n_groups):
        offset = (j - n_groups / 2 + 0.5) * bar_width
        bars = ax.bar(x_pos + offset, matrix[:, j], bar_width,
                       label=group_labels[j] if j < len(group_labels) else f"Group {j}",
                       color=mpl_colors[j] if j < len(mpl_colors) else None)

        if show_labels:
            for bar_rect in bars:
                height = bar_rect.get_height()
                ax.text(bar_rect.get_x() + bar_rect.get_width() / 2., height + 0.5,
                        label_format.format(height),
                        ha='center', va='bottom', fontweight='bold',
                        color=_parse_rgb("rgb(0,0,173)") if len(colors) > 0 else 'blue',
                        fontsize=9)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories if isinstance(categories, list) else [str(c) for c in categories])
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.12), ncol=n_groups, frameon=False)
    ax.set_ylim(0, matrix.max() * 1.15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def _plotly_grouped_bar(data, x, y, group, title, colors, ylabel, xlabel,
                         show_labels, label_format, save_path):
    """Create grouped bar chart using plotly."""
    import plotly.graph_objects as go

    fig = go.Figure()

    if isinstance(data, dict):
        categories = list(data.keys())
        for i, (cat, values) in enumerate(data.items()):
            color = colors[i % len(colors)] if colors else None
            fig.add_trace(go.Bar(
                name=cat,
                x=categories if isinstance(values, (int, float)) else list(range(len(values))),
                y=[values] if isinstance(values, (int, float)) else values,
                marker_color=color,
                text=(
                    [label_format.format(v) for v in (
                        [values] if isinstance(values, (int, float)) else values
                    )] if show_labels else None
                ),
                textposition='outside',
            ))
    elif isinstance(data, pl.DataFrame):
        if group and group in data.columns:
            for i, grp in enumerate(data[group].unique().sort().to_list()):
                subset = data.filter(pl.col(group) == grp)
                color = colors[i % len(colors)] if colors else None
                fig.add_trace(go.Bar(
                    name=str(grp),
                    x=subset[x].to_list() if isinstance(x, str) else x,
                    y=subset[y if isinstance(y, str) else y[0]].to_list(),
                    marker_color=color,
                    text=(
                        [label_format.format(v) for v in
                         subset[y if isinstance(y, str) else y[0]].to_list()]
                        if show_labels else None
                    ),
                    textposition='outside',
                ))

    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        barmode='group',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    if save_path:
        fig.write_image(save_path)

    return fig


def export_table(
    data: pl.DataFrame,
    path: str,
    float_format: str = "%.2f",
) -> None:
    """Export a survey estimates table to CSV.

    Args:
        data: polars DataFrame with estimation results.
        path: Output file path (.csv).
        float_format: Format for floating point numbers.
    """
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data.write_csv(str(output_path), float_precision=6)
