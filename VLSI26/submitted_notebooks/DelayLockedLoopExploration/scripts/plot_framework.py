"""
Interactive Pretty Graph Goes BRR

Usage in Jupyter Notebook:
    from bokeh.io import output_notebook
    output_notebook()

    from bokeh.io import output_notebook
    output_notebook()

    from plot_framework import (
        iplot, isweep, ioverlay, isweep_overlay,
        ianimate, ianimate_overlay, ianimate_stack, istack,
    )

    iplot(x, y, ...)
    isweep({label: (x, y)}, ...)                              # 1 slider
    isweep(nested_dict, ...)                                   # N sliders
    ioverlay({label: (x, y)}, ...)                             # legend toggle
    isweep_overlay({label: {trace: (x, y)}}, ...)              # 1 slider + legend
    isweep_overlay(deep_nested_dict_with_trace_leaves, ...)    # N sliders + legend
    ianimate(x, y, ...)                                        # progressive draw + play/pause
    ianimate_overlay({label: (x, y)}, ...)                     # multi-trace progressive draw
    ianimate_stack([{label: (x,y)}, ...], ...)                 # animated stacked subplots
"""

import numpy as np
from bokeh.plotting import figure, show
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    Slider,
    HoverTool,
    CrosshairTool,
    Div,
    Range1d
)
from bokeh.layouts import column, gridplot


COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]


def _make_figure(
    title, xlabel, ylabel, width, height, x_axis_type="linear", y_axis_type="linear"
):
    hover = HoverTool(tooltips=[("x", "$x{0.000}"), ("y", "$y{0.000}")])
    crosshair = CrosshairTool()
    p = figure(
        title=title,
        x_axis_label=xlabel,
        y_axis_label=ylabel,
        width=width,
        height=height,
        x_axis_type=x_axis_type,
        y_axis_type=y_axis_type,
        tools=[hover, crosshair, "box_zoom", "reset", "save", "pan", "wheel_zoom"],
        active_drag=None,
        active_scroll=None,
    )
    p.title.text_font_size = "14px"
    p.xaxis.axis_label_text_font_size = "12px"
    p.yaxis.axis_label_text_font_size = "12px"
    p.grid.grid_line_alpha = 0.3
    return p


def _add_trace(p, source, kind, color, label, line_width=2, size=6):
    kind = kind.lower().strip()
    if kind == "line":
        return [
            p.line(
                "x",
                "y",
                source=source,
                color=color,
                line_width=line_width,
                legend_label=label,
            )
        ]
    elif kind == "scatter":
        return [
            p.scatter(
                "x", "y", source=source, color=color, size=size, legend_label=label
            )
        ]
    elif kind == "line+scatter":
        r1 = p.line(
            "x",
            "y",
            source=source,
            color=color,
            line_width=line_width,
            legend_label=label,
        )
        r2 = p.scatter("x", "y", source=source, color=color, size=size)
        return [r1, r2]
    elif kind == "step":
        return [
            p.step(
                "x",
                "y",
                source=source,
                color=color,
                line_width=line_width,
                mode="after",
                legend_label=label,
            )
        ]
    elif kind == "area":
        r1 = p.line(
            "x",
            "y",
            source=source,
            color=color,
            line_width=line_width,
            legend_label=label,
        )
        r2 = p.varea(x="x", y1=0, y2="y", source=source, color=color, alpha=0.2)
        return [r1, r2]
    elif kind == "bar":
        return [
            p.vbar(
                x="x",
                top="y",
                source=source,
                color=color,
                width=0.7,
                alpha=0.7,
                legend_label=label,
            )
        ]
    elif kind in ("histogram", "hist"):
        y_data = np.array(source.data["y"])
        counts, edges = np.histogram(y_data, bins="auto")
        hist_source = ColumnDataSource(
            data=dict(
                top=counts,
                left=edges[:-1],
                right=edges[1:],
            )
        )
        return [
            p.quad(
                top="top",
                bottom=0,
                left="left",
                right="right",
                source=hist_source,
                color=color,
                alpha=0.65,
                line_color="white",
                legend_label=label,
            )
        ]
    elif kind in ("bell", "bell curve", "kde"):
        from scipy.stats import gaussian_kde

        y_data = np.array(source.data["y"])
        kde = gaussian_kde(y_data)
        xs = np.linspace(
            y_data.min() - 3 * y_data.std(), y_data.max() + 3 * y_data.std(), 500
        )
        ys = kde(xs)
        kde_source = ColumnDataSource(data=dict(x=xs, y=ys))
        r1 = p.line(
            "x",
            "y",
            source=kde_source,
            color=color,
            line_width=line_width,
            legend_label=label,
        )
        r2 = p.varea(x="x", y1=0, y2="y", source=kde_source, color=color, alpha=0.15)
        return [r1, r2]
    else:
        raise ValueError(
            f"Unknown kind '{kind}'. Choose from: line, scatter, "
            f"line+scatter, step, area, bar, histogram, bell/kde"
        )


def _style_legend(p, location="top_right"):
    if p.legend and len(p.legend) > 0:
        legend = p.legend[0]
        legend.click_policy = "hide"
        legend.location = location
        legend.label_text_font_size = "10px"
        legend.background_fill_alpha = 0.7
        legend.border_line_alpha = 0.3


def _is_xy_tuple(v):
    """Check if v looks like an (x, y) data pair."""
    return isinstance(v, (tuple, list)) and len(v) == 2 and not isinstance(v[0], str)


def _parse_sweep_tree(tree):
    """
    Recursively walk a nested dict and return:
        levels  : list of lists-of-labels, one per nesting level (= slider)
        flat    : list of leaf values in row-major order

    Leaf values are whatever sits at the bottom of the nesting — either
    (x, y) tuples (for isweep) or dicts of {trace: (x, y)} (for isweep_overlay).
    """
    # Base case: value is a leaf (x, y) tuple
    first_val = next(iter(tree.values()))
    if _is_xy_tuple(first_val):
        labels = list(tree.keys())
        return [labels], list(tree.values())

    # Recursive case: this level is a sweep dimension
    labels = list(tree.keys())
    sub_levels = None
    flat = []
    for key in labels:
        child_levels, child_flat = _parse_sweep_tree(tree[key])
        if sub_levels is None:
            sub_levels = child_levels
        flat.extend(child_flat)
    return [labels] + sub_levels, flat


def _parse_sweep_overlay_tree(tree):
    """
    Like _parse_sweep_tree but the leaf is a dict {trace_label: (x,y)}.
    Returns:
        levels      : list of lists-of-labels (one per slider)
        trace_names : list of trace labels (consistent across all leaves)
        flat        : list of dicts {trace: (x,y)} in row-major order
    """
    first_val = next(iter(tree.values()))

    # Check if this level is the overlay-leaf level:
    # it's a dict whose values are all (x,y) tuples
    if isinstance(first_val, dict):
        inner_first = next(iter(first_val.values()))
        if _is_xy_tuple(inner_first):
            labels = list(tree.keys())
            return [labels], list(first_val.keys()), list(tree.values())

    # Otherwise recurse
    labels = list(tree.keys())
    sub_levels = None
    trace_names = None
    flat = []
    for key in labels:
        child_levels, child_traces, child_flat = _parse_sweep_overlay_tree(tree[key])
        if sub_levels is None:
            sub_levels = child_levels
            trace_names = child_traces
        flat.extend(child_flat)
    return [labels] + sub_levels, trace_names, flat


def _flat_index(indices, dims):
    """Row-major flat index from a list of per-dimension indices."""
    idx = 0
    for i, d in zip(indices, dims):
        idx = idx * d + i
    return idx


"""
PUBLIC FUNCTIONS TO USE
"""


def iplot(
    x,
    y,
    *,
    title="",
    xlabel="x",
    ylabel="y",
    kind="line",
    color=None,
    width=800,
    height=450,
    x_log=False,
    y_log=False,
):
    """Plot a single dataset."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    source = ColumnDataSource(data=dict(x=x, y=y))
    p = _make_figure(
        title,
        xlabel,
        ylabel,
        width,
        height,
        x_axis_type="log" if x_log else "linear",
        y_axis_type="log" if y_log else "linear",
    )
    _add_trace(p, source, kind, color or COLORS[0], label=title or "data")
    if p.legend and len(p.legend) > 0:
        p.legend.visible = False
    show(p)


def ioverlay(
    datasets,
    *,
    title="",
    xlabel="x",
    ylabel="y",
    kind="line",
    width=800,
    height=450,
    x_log=False,
    y_log=False,
):
    """Overlay multiple datasets. Click legend to hide/show."""
    p = _make_figure(
        title,
        xlabel,
        ylabel,
        width,
        height,
        x_axis_type="log" if x_log else "linear",
        y_axis_type="log" if y_log else "linear",
    )
    for i, (label, (x, y)) in enumerate(datasets.items()):
        source = ColumnDataSource(
            data=dict(x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float))
        )
        _add_trace(p, source, kind, COLORS[i % len(COLORS)], label=label)
    _style_legend(p)
    show(p)


def isweep(
    datasets,
    *,
    title="",
    xlabel="x",
    ylabel="y",
    kind="line",
    width=800,
    height=450,
    x_log=False,
    y_log=False,
):
    """
    N-dimensional sweep with one slider per nesting level.

    Parameters
    ----------
    datasets : nested dict
        Any depth of {label: ...} nesting. Leaves are (x, y) tuples.
        1 level  → 1 slider.   2 levels → 2 sliders.   N levels → N sliders.

    Examples
    --------
    # 1-slider
    isweep({"a": (x, y), "b": (x, y)})

    # 2-slider
    isweep({"T=25": {"VDD=0.9": (x,y), "VDD=1.1": (x,y)},
            "T=85": {"VDD=0.9": (x,y), "VDD=1.1": (x,y)}})
    """
    levels, flat_data = _parse_sweep_tree(datasets)
    n_dims = len(levels)
    dims = [len(lvl) for lvl in levels]

    # Pre-process data for kinds that derive display data from raw samples
    render_kind = kind
    if kind in ("bell", "kde"):
        from scipy.stats import gaussian_kde

        processed = []
        for _, y_raw in flat_data:
            samples = np.asarray(y_raw, dtype=float)
            kde = gaussian_kde(samples)
            xs = np.linspace(
                samples.min() - 3 * samples.std(),
                samples.max() + 3 * samples.std(),
                500,
            )
            ys = kde(xs)
            processed.append((xs, ys))
        flat_data = processed
        render_kind = "area"
    elif kind in ("histogram", "hist"):
        processed = []
        for _, y_raw in flat_data:
            samples = np.asarray(y_raw, dtype=float)
            counts, edges = np.histogram(samples, bins="auto")
            centers = (edges[:-1] + edges[1:]) / 2
            processed.append((centers, counts))
        flat_data = processed
        render_kind = "bar"

    # Build flat source array
    all_sources = []
    for xy in flat_data:
        x, y = xy
        all_sources.append(
            ColumnDataSource(
                data=dict(x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float))
            )
        )

    # Active source
    first_x, first_y = flat_data[0]
    active_source = ColumnDataSource(
        data=dict(
            x=np.asarray(first_x, dtype=float), y=np.asarray(first_y, dtype=float)
        )
    )

    p = _make_figure(
        title,
        xlabel,
        ylabel,
        width,
        height,
        x_axis_type="log" if x_log else "linear",
        y_axis_type="log" if y_log else "linear",
    )
    _add_trace(
        p,
        active_source,
        render_kind,
        COLORS[0],
        label=levels[0][0] if levels else "data",
    )
    if p.legend:
        p.legend.visible = False

    # Label showing current selection
    init_label = "  &middot;  ".join(lvl[0] for lvl in levels)
    label_div = Div(
        text=f"<b style='font-size:13px;'>{init_label}</b>",
        width=width,
        styles={"text-align": "center"},
    )

    # Build sliders
    sliders = []
    for d in range(n_dims):
        s = Slider(
            start=0,
            end=dims[d] - 1,
            value=0,
            step=1,
            title="",
            show_value=False,
            width=width - 60,
        )
        sliders.append(s)

    # Single JS callback shared by all sliders
    # Each slider is passed as s0, s1, ... to avoid circular reference
    # (slider -> callback -> sliders list -> slider)
    slider_idx_code = " ".join(f"indices.push(s{d}.value);" for d in range(n_dims))
    js_code = f"""
        const indices = [];
        {slider_idx_code}
        let flat_idx = 0;
        for (let d = 0; d < dims.length; d++) {{
            flat_idx = flat_idx * dims[d] + indices[d];
        }}
        active.data = {{...all_sources[flat_idx].data}};
        active.change.emit();

        let parts = [];
        for (let d = 0; d < dims.length; d++) {{
            parts.push(levels[d][indices[d]]);
        }}
        label_div.text = "<b style='font-size:13px;'>" + parts.join("  &middot;  ") + "</b>";

        const color = colors[flat_idx % colors.length];
        for (const r of renderers) {{
            if (r.glyph && r.glyph.line_color !== undefined)
                r.glyph.line_color = color;
            if (r.glyph && r.glyph.fill_color !== undefined)
                r.glyph.fill_color = color;
        }}
    """

    cb_args = dict(
        active=active_source,
        all_sources=all_sources,
        levels=levels,
        dims=dims,
        label_div=label_div,
        renderers=p.renderers,
        colors=COLORS,
    )
    for d, s in enumerate(sliders):
        cb_args[f"s{d}"] = s

    for s in sliders:
        s.js_on_change("value", CustomJS(args=cb_args, code=js_code))

    layout = column(p, label_div, *sliders, sizing_mode="fixed")
    show(layout)


def isweep_overlay(
    sweep_groups,
    *,
    title="",
    xlabel="x",
    ylabel="y",
    kind="line",
    width=800,
    height=450,
    x_log=False,
    y_log=False,
):
    """
    N-dimensional sweep + overlaid traces with legend hide/show.

    Parameters
    ----------
    sweep_groups : nested dict
        Any depth of {label: ...} nesting. Innermost dict maps
        trace labels to (x, y) tuples.

    Examples
    --------
    # 1-slider + overlay
    isweep_overlay({
        "VDD=0.9": {"trace_a": (x,y), "trace_b": (x,y)},
        "VDD=1.1": {"trace_a": (x,y), "trace_b": (x,y)},
    })

    # 2-slider + overlay
    isweep_overlay({
        "T=25": {
            "VDD=0.9": {"trace_a": (x,y), "trace_b": (x,y)},
            "VDD=1.1": {"trace_a": (x,y), "trace_b": (x,y)},
        },
        "T=85": { ... },
    })
    """
    levels, trace_names, flat_data = _parse_sweep_overlay_tree(sweep_groups)
    n_dims = len(levels)
    dims = [len(lvl) for lvl in levels]
    n_traces = len(trace_names)

    # Active sources — one per trace
    first_cell = flat_data[0]
    active_sources = []
    for tname in trace_names:
        x, y = first_cell[tname]
        active_sources.append(
            ColumnDataSource(
                data=dict(x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float))
            )
        )

    # Master: flat list of lists-of-sources, one inner list per grid cell
    all_cells = []
    for cell_dict in flat_data:
        cell_srcs = []
        for tname in trace_names:
            x, y = cell_dict[tname]
            cell_srcs.append(
                ColumnDataSource(
                    data=dict(
                        x=np.asarray(x, dtype=float), y=np.asarray(y, dtype=float)
                    )
                )
            )
        all_cells.append(cell_srcs)

    p = _make_figure(
        title,
        xlabel,
        ylabel,
        width,
        height,
        x_axis_type="log" if x_log else "linear",
        y_axis_type="log" if y_log else "linear",
    )

    for i, tname in enumerate(trace_names):
        _add_trace(p, active_sources[i], kind, COLORS[i % len(COLORS)], label=tname)

    _style_legend(p)

    init_label = "  &middot;  ".join(lvl[0] for lvl in levels)
    label_div = Div(
        text=f"<b style='font-size:13px;'>{init_label}</b>",
        width=width,
        styles={"text-align": "center"},
    )

    sliders = []
    for d in range(n_dims):
        s = Slider(
            start=0,
            end=dims[d] - 1,
            value=0,
            step=1,
            title="",
            show_value=False,
            width=width - 60,
        )
        sliders.append(s)

    slider_idx_code = " ".join(f"indices.push(s{d}.value);" for d in range(n_dims))
    js_code = f"""
        const indices = [];
        {slider_idx_code}
        let flat_idx = 0;
        for (let d = 0; d < dims.length; d++) {{
            flat_idx = flat_idx * dims[d] + indices[d];
        }}
        const cell = all_cells[flat_idx];
        for (let t = 0; t < active_sources.length; t++) {{
            active_sources[t].data = {{...cell[t].data}};
            active_sources[t].change.emit();
        }}
        let parts = [];
        for (let d = 0; d < dims.length; d++) {{
            parts.push(levels[d][indices[d]]);
        }}
        label_div.text = "<b style='font-size:13px;'>" + parts.join("  &middot;  ") + "</b>";
    """

    cb_args = dict(
        active_sources=active_sources,
        all_cells=all_cells,
        levels=levels,
        dims=dims,
        label_div=label_div,
    )
    for d, s in enumerate(sliders):
        cb_args[f"s{d}"] = s

    for s in sliders:
        s.js_on_change("value", CustomJS(args=cb_args, code=js_code))

    layout = column(p, label_div, *sliders, sizing_mode="fixed")
    show(layout)


def ianimate(
    x,
    y,
    *,
    title="",
    xlabel="x",
    ylabel="y",
    kind="line",
    color=None,
    width=800,
    height=450,
    x_log=False,
    y_log=False,
    interval_ms=50,
    step_size=1,
):
    """
    Progressively draw a single trace over time with play/pause + scrub slider.

    The slider controls how many data points are visible. Pressing Play
    auto-advances the slider from its current position to the end.

    Parameters
    ----------
    x, y        : array-like data (same length)
    interval_ms : milliseconds between animation frames
    step_size   : how many points to reveal per frame
    (all other params match iplot)

    Usage
    -----
        ianimate(time, voltage, title="Transient", xlabel="t (ns)", ylabel="V")
    """
    from bokeh.models import Button

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)

    # Full data lives in a hidden source; active source gets sliced
    full_source = ColumnDataSource(data=dict(x=x, y=y))
    active_source = ColumnDataSource(data=dict(x=x[:1], y=y[:1]))

    p = _make_figure(
        title, xlabel, ylabel, width, height,
        x_axis_type="log" if x_log else "linear",
        y_axis_type="log" if y_log else "linear",
    )
    # Lock axis ranges to the full data extent so the view doesn't jump
    x_pad = (x.max() - x.min()) * 0.02 or 1.0
    y_pad = (y.max() - y.min()) * 0.05 or 1.0
    p.x_range = Range1d(start=x.min() - x_pad, end=x.max() + x_pad)
    p.y_range = Range1d(start=y.min() - y_pad, end=y.max() + y_pad)

    _add_trace(p, active_source, kind, color or COLORS[0], label=title or "data")
    if p.legend and len(p.legend) > 0:
        p.legend.visible = False

    slider = Slider(
        start=1, end=n, value=1, step=step_size,
        title=f"Samples shown (1 – {n})",
        width=width - 60,
    )

    btn_play = Button(label="Play", button_type="success", width=80)
    btn_pause = Button(label="Pause", button_type="warning", width=80)

    # Slider → slice the full source
    slider_cb = CustomJS(
        args=dict(active=active_source, full=full_source, slider=slider),
        code="""
            const k = slider.value;
            active.data = {
                x: full.data.x.slice(0, k),
                y: full.data.y.slice(0, k),
            };
            active.change.emit();
        """,
    )
    slider.js_on_change("value", slider_cb)

    # Play → start a JS interval that increments the slider
    play_cb = CustomJS(
        args=dict(slider=slider, btn_play=btn_play),
        code=f"""
            // Store interval ID on the button model so Pause can find it
            if (btn_play._interval_id) return;          // already playing
            btn_play._interval_id = setInterval(() => {{
                if (slider.value >= slider.end) {{
                    clearInterval(btn_play._interval_id);
                    btn_play._interval_id = null;
                    return;
                }}
                slider.value = Math.min(slider.value + {step_size}, slider.end);
            }}, {interval_ms});
        """,
    )
    btn_play.js_on_click(play_cb)

    # Pause → clear the interval
    pause_cb = CustomJS(
        args=dict(btn_play=btn_play),
        code="""
            if (btn_play._interval_id) {
                clearInterval(btn_play._interval_id);
                btn_play._interval_id = null;
            }
        """,
    )
    btn_pause.js_on_click(pause_cb)

    from bokeh.layouts import row as bk_row
    controls = bk_row(btn_play, btn_pause)
    layout = column(p, slider, controls, sizing_mode="fixed")
    show(layout)


def ianimate_overlay(
    datasets,
    *,
    title="",
    xlabel="x",
    ylabel="y",
    kind="line",
    width=800,
    height=450,
    x_log=False,
    y_log=False,
    interval_ms=50,
    step_size=1,
):
    """
    Progressively draw multiple overlaid traces in sync with play/pause + scrub.

    Parameters
    ----------
    datasets : dict  {label: (x, y), ...}
        Same format as ioverlay. All traces are scrubbed together by the
        same slider (they must share the same x-axis length, or each is
        clipped to its own length).

    Usage
    -----
        ianimate_overlay({
            "ch1": (t, v1),
            "ch2": (t, v2),
        }, title="Multi-channel capture", interval_ms=30)
    """
    from bokeh.models import Button

    # Build full + active sources for every trace
    entries = list(datasets.items())
    max_n = 0
    full_sources = []
    active_sources = []
    for label, (x, y) in entries:
        xa = np.asarray(x, dtype=float)
        ya = np.asarray(y, dtype=float)
        max_n = max(max_n, len(xa))
        full_sources.append(ColumnDataSource(data=dict(x=xa, y=ya)))
        active_sources.append(ColumnDataSource(data=dict(x=xa[:1], y=ya[:1])))

    p = _make_figure(
        title, xlabel, ylabel, width, height,
        x_axis_type="log" if x_log else "linear",
        y_axis_type="log" if y_log else "linear",
    )

    # Lock axes to full data extent
    all_x = np.concatenate([s.data["x"] for s in full_sources])
    all_y = np.concatenate([s.data["y"] for s in full_sources])
    x_pad = (all_x.max() - all_x.min()) * 0.02 or 1.0
    y_pad = (all_y.max() - all_y.min()) * 0.05 or 1.0
    p.x_range = Range1d(start=all_x.min() - x_pad, end=all_x.max() + x_pad)
    p.y_range = Range1d(start=all_y.min() - y_pad, end=all_y.max() + y_pad)

    for i, (label, _) in enumerate(entries):
        _add_trace(p, active_sources[i], kind, COLORS[i % len(COLORS)], label=label)
    _style_legend(p)

    slider = Slider(
        start=1, end=max_n, value=1, step=step_size,
        title=f"Samples shown (1 – {max_n})",
        width=width - 60,
    )

    btn_play = Button(label="Play", button_type="success", width=80)
    btn_pause = Button(label="Pause", button_type="warning", width=80)

    slider_cb = CustomJS(
        args=dict(active_sources=active_sources, full_sources=full_sources, slider=slider),
        code="""
            const k = slider.value;
            for (let i = 0; i < active_sources.length; i++) {
                const f = full_sources[i].data;
                const slice_end = Math.min(k, f.x.length);
                active_sources[i].data = {
                    x: f.x.slice(0, slice_end),
                    y: f.y.slice(0, slice_end),
                };
                active_sources[i].change.emit();
            }
        """,
    )
    slider.js_on_change("value", slider_cb)

    play_cb = CustomJS(
        args=dict(slider=slider, btn_play=btn_play),
        code=f"""
            if (btn_play._interval_id) return;
            btn_play._interval_id = setInterval(() => {{
                if (slider.value >= slider.end) {{
                    clearInterval(btn_play._interval_id);
                    btn_play._interval_id = null;
                    return;
                }}
                slider.value = Math.min(slider.value + {step_size}, slider.end);
            }}, {interval_ms});
        """,
    )
    btn_play.js_on_click(play_cb)

    pause_cb = CustomJS(
        args=dict(btn_play=btn_play),
        code="""
            if (btn_play._interval_id) {
                clearInterval(btn_play._interval_id);
                btn_play._interval_id = null;
            }
        """,
    )
    btn_pause.js_on_click(pause_cb)

    from bokeh.layouts import row as bk_row
    controls = bk_row(btn_play, btn_pause)
    layout = column(p, slider, controls, sizing_mode="fixed")
    show(layout)


def istack(
    layers: list[dict],
    *,
    title: str = "",
    xlabel: str = "x",
    ylabels: list[str] | None = None,
    kind: str = "line",
    width: int = 900,
    layer_height: int = 180,
    x_range: tuple[float, float] | None = None,
    x_log: bool = False,
    y_log: bool = False,
    colors: list[str] | None = None,
):
    """
    Vertically stacked subplots sharing one x-axis.

    Parameters
    ----------
    layers : list of dicts
        Each dict maps {label: (x, y)} — same format as ioverlay.
        Layers are drawn top-to-bottom. Each layer becomes one
        subplot. Multiple signals in one layer are overlaid with
        legend toggle.

    title       : title for the top subplot
    xlabel      : x-axis label (shown only on the bottom subplot)
    ylabels     : per-layer y-axis labels; if None, auto-generated
                  from the signal names in each layer
    kind        : trace type ("line", "scatter", "line+scatter", "step")
    width       : figure width in pixels
    layer_height: height per subplot in pixels
    x_range     : optional (min, max) to lock the shared x-axis
    x_log       : log scale on x-axis
    y_log       : log scale on y-axis
    colors      : custom color palette (defaults to framework COLORS)
    """
    if not layers:
        raise ValueError("Need at least one layer")

    palette = colors or COLORS
    n_layers = len(layers)

    # Auto-generate y-labels from signal names if not provided
    if ylabels is None:
        ylabels = [", ".join(layer.keys()) for layer in layers]
    elif len(ylabels) < n_layers:
        ylabels = list(ylabels) + [""] * (n_layers - len(ylabels))

    # Compute shared x-range from all data if not given
    if x_range is None:
        x_min, x_max = np.inf, -np.inf
        for layer in layers:
            for x, _ in layer.values():
                x_arr = np.asarray(x, dtype=float)
                x_min = min(x_min, x_arr.min())
                x_max = max(x_max, x_arr.max())
        shared_x_range = Range1d(start=x_min, end=x_max)
    else:
        shared_x_range = Range1d(start=x_range[0], end=x_range[1])

    figures = []
    color_idx = 0  # Global color counter so colors don't repeat
    # across layers unless the palette wraps

    for i, layer in enumerate(layers):
        is_top = i == 0
        is_bottom = i == n_layers - 1

        hover = HoverTool(tooltips=[("x", "$x{0.000}"), ("y", "$y{0.000}")])
        crosshair = CrosshairTool()

        p = figure(
            title=title if is_top else None,
            x_axis_label=xlabel if is_bottom else None,
            y_axis_label=ylabels[i],
            width=width,
            height=layer_height + (30 if is_top else 0) + (30 if is_bottom else 0),
            x_range=shared_x_range,
            x_axis_type="log" if x_log else "linear",
            y_axis_type="log" if y_log else "linear",
            tools=[
                hover,
                crosshair,
                "box_zoom",
                "xpan",
                "xwheel_zoom",
                "reset",
                "save",
            ],
            active_drag="xpan",
            active_scroll="xwheel_zoom",
        )

        # Style
        if is_top:
            p.title.text_font_size = "14px"
        p.yaxis.axis_label_text_font_size = "11px"
        p.grid.grid_line_alpha = 0.3
        p.min_border_top = 8 if not is_top else 20
        p.min_border_bottom = 8 if not is_bottom else 40

        # Hide x-axis ticks/labels on non-bottom plots
        if not is_bottom:
            p.xaxis.visible = False

        # Plot traces in this layer
        for label, (x, y) in layer.items():
            source = ColumnDataSource(
                data=dict(
                    x=np.asarray(x, dtype=float),
                    y=np.asarray(y, dtype=float),
                )
            )
            c = palette[color_idx % len(palette)]
            _add_trace(p, source, kind, c, label=label)
            color_idx += 1

        # Only show legend if the layer has multiple signals
        if len(layer) > 1:
            _style_legend(p, location="top_right")
        elif p.legend and len(p.legend) > 0:
            p.legend.visible = False

        figures.append(p)

    grid = gridplot(
        [[fig] for fig in figures],
        merge_tools=True,
        toolbar_location="right",
    )
    show(grid)


def ianimate_stack(
    layers: list[dict],
    *,
    title: str = "",
    xlabel: str = "x",
    ylabels: list[str] | None = None,
    kind: str = "line",
    width: int = 900,
    layer_height: int = 180,
    x_range: tuple[float, float] | None = None,
    x_log: bool = False,
    y_log: bool = False,
    colors: list[str] | None = None,
    interval_ms: int = 50,
    step_size: int = 1,
):
    """
    Animated vertically stacked subplots — progressive draw with
    play/pause and a shared scrub slider.

    All traces across all layers are revealed in sync by one slider.

    Parameters
    ----------
    layers : list of dicts
        Each dict maps {label: (x, y)} — same format as istack / ioverlay.
        Each layer becomes one subplot; multiple signals in a layer are
        overlaid with legend toggle.

    title        : title for the top subplot
    xlabel       : x-axis label (bottom subplot only)
    ylabels      : per-layer y-axis labels; None → auto from signal names
    kind         : trace type ("line", "scatter", "line+scatter", "step")
    width        : figure width in pixels
    layer_height : height per subplot in pixels
    x_range      : optional (min, max) to lock the shared x-axis
    x_log        : log scale on x-axis
    y_log        : log scale on y-axis
    colors       : custom color palette (defaults to framework COLORS)
    interval_ms  : milliseconds between animation frames
    step_size    : how many points to reveal per frame

    Usage
    -----
        t = np.linspace(0, 10, 2000)
        ianimate_stack([
            {"Voltage": (t, np.sin(2*t))},
            {"Current": (t, np.cos(2*t) * 0.5)},
            {"Power":   (t, np.sin(2*t) * np.cos(2*t) * 0.5)},
        ], title="Circuit Waveforms", xlabel="t (ns)",
           ylabels=["V", "I", "P"], interval_ms=20, step_size=5)
    """
    from bokeh.models import Button
    from bokeh.layouts import row as bk_row

    if not layers:
        raise ValueError("Need at least one layer")

    palette = colors or COLORS
    n_layers = len(layers)

    if ylabels is None:
        ylabels = [", ".join(layer.keys()) for layer in layers]
    elif len(ylabels) < n_layers:
        ylabels = list(ylabels) + [""] * (n_layers - len(ylabels))

    # ── Collect full/active source pairs across ALL layers ──
    # We need flat lists so the JS callback can iterate once.
    all_full_sources = []
    all_active_sources = []
    # Also track which sources belong to which layer for plotting
    layer_source_ranges = []   # list of (start_idx, count)

    max_n = 0
    x_min_global, x_max_global = np.inf, -np.inf
    y_extremes_per_layer = []  # [(ymin, ymax), ...]

    for layer in layers:
        start = len(all_full_sources)
        y_lo, y_hi = np.inf, -np.inf
        for label, (x, y) in layer.items():
            xa = np.asarray(x, dtype=float)
            ya = np.asarray(y, dtype=float)
            max_n = max(max_n, len(xa))
            x_min_global = min(x_min_global, xa.min())
            x_max_global = max(x_max_global, xa.max())
            y_lo = min(y_lo, ya.min())
            y_hi = max(y_hi, ya.max())
            all_full_sources.append(ColumnDataSource(data=dict(x=xa, y=ya)))
            all_active_sources.append(ColumnDataSource(data=dict(x=xa[:1], y=ya[:1])))
        y_extremes_per_layer.append((y_lo, y_hi))
        layer_source_ranges.append((start, len(all_full_sources) - start))

    # Shared x-range
    if x_range is None:
        shared_x_range = Range1d(start=x_min_global, end=x_max_global)
    else:
        shared_x_range = Range1d(start=x_range[0], end=x_range[1])

    # ── Build subplot figures ──
    figures = []
    color_idx = 0

    for i, layer in enumerate(layers):
        is_top = i == 0
        is_bottom = i == n_layers - 1

        hover = HoverTool(tooltips=[("x", "$x{0.000}"), ("y", "$y{0.000}")])
        crosshair = CrosshairTool()

        p = figure(
            title=title if is_top else None,
            x_axis_label=xlabel if is_bottom else None,
            y_axis_label=ylabels[i],
            width=width,
            height=layer_height + (30 if is_top else 0) + (30 if is_bottom else 0),
            x_range=shared_x_range,
            x_axis_type="log" if x_log else "linear",
            y_axis_type="log" if y_log else "linear",
            tools=[
                hover, crosshair,
                "box_zoom", "xpan", "xwheel_zoom", "reset", "save",
            ],
            active_drag="xpan",
            active_scroll="xwheel_zoom",
        )

        # Lock y-range so subplots don't auto-rescale during animation
        y_lo, y_hi = y_extremes_per_layer[i]
        y_pad = (y_hi - y_lo) * 0.05 or 1.0
        p.y_range = Range1d(start=y_lo - y_pad, end=y_hi + y_pad)

        if is_top:
            p.title.text_font_size = "14px"
        p.yaxis.axis_label_text_font_size = "11px"
        p.grid.grid_line_alpha = 0.3
        p.min_border_top = 8 if not is_top else 20
        p.min_border_bottom = 8 if not is_bottom else 40

        if not is_bottom:
            p.xaxis.visible = False

        # Plot traces using the active sources
        src_start, src_count = layer_source_ranges[i]
        for j, (label, _) in enumerate(layer.items()):
            active_src = all_active_sources[src_start + j]
            c = palette[color_idx % len(palette)]
            _add_trace(p, active_src, kind, c, label=label)
            color_idx += 1

        if len(layer) > 1:
            _style_legend(p, location="top_right")
        elif p.legend and len(p.legend) > 0:
            p.legend.visible = False

        figures.append(p)

    # ── Slider + Play/Pause ──
    slider = Slider(
        start=1, end=max_n, value=1, step=step_size,
        title=f"Samples shown (1 – {max_n})",
        width=width - 60,
    )

    btn_play = Button(label="Play", button_type="success", width=80)
    btn_pause = Button(label="Pause", button_type="warning", width=80)

    slider_cb = CustomJS(
        args=dict(
            active_sources=all_active_sources,
            full_sources=all_full_sources,
            slider=slider,
        ),
        code="""
            const k = slider.value;
            for (let i = 0; i < active_sources.length; i++) {
                const f = full_sources[i].data;
                const slice_end = Math.min(k, f.x.length);
                active_sources[i].data = {
                    x: f.x.slice(0, slice_end),
                    y: f.y.slice(0, slice_end),
                };
                active_sources[i].change.emit();
            }
        """,
    )
    slider.js_on_change("value", slider_cb)

    play_cb = CustomJS(
        args=dict(slider=slider, btn_play=btn_play),
        code=f"""
            if (btn_play._interval_id) return;
            btn_play._interval_id = setInterval(() => {{
                if (slider.value >= slider.end) {{
                    clearInterval(btn_play._interval_id);
                    btn_play._interval_id = null;
                    return;
                }}
                slider.value = Math.min(slider.value + {step_size}, slider.end);
            }}, {interval_ms});
        """,
    )
    btn_play.js_on_click(play_cb)

    pause_cb = CustomJS(
        args=dict(btn_play=btn_play),
        code="""
            if (btn_play._interval_id) {
                clearInterval(btn_play._interval_id);
                btn_play._interval_id = null;
            }
        """,
    )
    btn_pause.js_on_click(pause_cb)

    # ── Layout: grid on top, controls below ──
    grid = gridplot(
        [[fig] for fig in figures],
        merge_tools=True,
        toolbar_location="right",
    )
    controls = bk_row(btn_play, btn_pause)
    layout = column(grid, slider, controls, sizing_mode="fixed")
    show(layout)
