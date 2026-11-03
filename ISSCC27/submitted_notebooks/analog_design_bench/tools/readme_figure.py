"""Draw the README's model-score figure and its time-and-cost figures from the frozen data/ folder.

    python tools/readme_figure.py

Writes figures/pass_rate_by_model.png. Each bar shows two rates for one model:
the share of its 150 attempts that passed (dark) and the share of the 50 tasks it
solved in at least one of three attempts (light). The two strongest models are
highlighted. figures/pass_rate_and_spec_score.png has the same layout: the pass rate
(binary reward, dark) over the spec score (the verifier's reward with partial credit,
averaged over the 150 attempts, light). The two are drawn to sit side by side at half the README width.

Also writes figures/cost_vs_pass_rate.png (pass rate against API cost per attempt) and
figures/time_and_cost_by_model.png (minutes per attempt and cost per passing design), drawn to sit side
by side at half the README width, and rewrites the README section on time and cost (HEADING) to show them.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import FixedLocator, NullLocator
from matplotlib.transforms import Bbox

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adb import report  # noqa: E402

HIGHLIGHT = 2
ACCENT, ACCENT_LIGHT = "#2563a8", "#a9c4e6"
MUTED, MUTED_LIGHT = "#9aa1ab", "#dde0e5"
HALF = (4.8, 5.4)  # inches; each time-and-cost figure is shown at about 420 px, two to a row
HEADING = "## What AI-designed circuits cost"


def main() -> None:
    tasks, models, attempts = report.load(ROOT)
    mt = report.model_table(models, attempts)
    plt.rcParams.update({"font.family": "sans-serif", "font.size": 9.5,
                         "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]})
    n_solved = mt["tasks solved (any of 3)"]
    # The verifier's reward is 1 for a pass and partial credit for the signoff checks a failing design meets;
    # its mean is the leaderboard's spec score.
    spec = attempts.groupby("model_slug").reward.mean()
    with plt.rc_context({"font.size": 8.5}):
        draw_two_rates(mt, mt["pass rate"], n_solved / len(tasks), "Pass rate and tasks solved",
                       ("Attempts passed", "Tasks solved in any of 3 attempts"),
                       lambda s: f"{mt.at[s, 'passes']}/{mt.at[s, 'attempts']} attempts, {n_solved[s]}/{len(tasks)} tasks",
                       "pass_rate_by_model.png")
        draw_two_rates(mt, mt["pass rate"], spec, "Pass rate and spec score",
                       ("Pass rate (binary reward)", "Spec score (partial credit)"),
                       lambda s: f"{mt.at[s, 'pass rate']:.1%} pass rate, {spec[s]:.1%} spec score",
                       "pass_rate_and_spec_score.png")
        draw_cost_scatter(mt)
        draw_time_and_cost(mt)
    write_time_and_cost(mt)


def draw_two_rates(mt, dark, light, title, legend, note, name) -> None:
    """One bar per model: the dark rate drawn over the light one (light >= dark), both as shares of 100%;
    the HIGHLIGHT strongest models are coloured and carry note(model_slug)."""
    fig, ax = plt.subplots(figsize=HALF)
    y = range(len(mt))
    top = [i < HIGHLIGHT for i in y]
    ax.barh(y, light[mt.index] * 100, height=0.66, color=[ACCENT_LIGHT if t else MUTED_LIGHT for t in top])
    ax.barh(y, dark[mt.index] * 100, height=0.66, color=[ACCENT if t else MUTED for t in top])
    for i, slug in enumerate(mt.index):
        if top[i]:
            ax.text(1.5, i, note(slug), va="center", color="white", fontsize=7, weight="bold")
    ax.set_yticks(list(y), [f"{r.model} ({r.provider})" for r in mt.itertuples()], fontsize=7.5)
    for label, t in zip(ax.get_yticklabels(), top):
        label.set_color("#111" if t else "#777")
    ax.set_ylim(len(mt) - 0.5, -0.5)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 50, 100], ["0%", "50%", "100%"], color="#777")
    ax.get_xticklabels()[-1].set_horizontalalignment("right")
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, color="#111", fontsize=9.5, loc="left")
    ax.legend(handles=[Patch(color=ACCENT, label=legend[0]), Patch(color=ACCENT_LIGHT, label=legend[1])],
              loc="lower right", frameon=False, fontsize=7.5)
    # Fixed margins rather than tight_layout, so the bars of the two side-by-side figures line up.
    fig.subplots_adjust(left=0.42, right=0.97, top=0.93, bottom=0.06)
    fig.savefig(ROOT / "figures" / name, dpi=200)


def tidy(ax) -> None:
    ax.tick_params(length=0, colors="#777")
    for spine in ax.spines.values():
        spine.set_visible(False)


def dollar_ticks(axis, ticks) -> None:
    axis.set_major_locator(FixedLocator(ticks))
    axis.set_minor_locator(NullLocator())
    axis.set_ticklabels([f"${t:g}" for t in ticks])


def label_points(fig, ax, xs, ys, labels, top) -> None:
    """Name every point without overlaps: the most crowded points pick first, from the nearest free offset;
    a label set off from its point gets a leader line."""
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    pts = ax.transData.transform(np.c_[xs, ys])
    taken = [Bbox.from_extents(px - 4, py - 4, px + 4, py + 4) for px, py in pts]
    crowd = [sum(np.hypot(*(q - p)) < 90 for q in pts) for p in pts]
    frame = ax.get_window_extent(renderer)
    dirs = [(1, 0, "left", "center"), (-1, 0, "right", "center"), (0, 1, "center", "bottom"),
            (0, -1, "center", "top"), (1, 1, "left", "bottom"), (1, -1, "left", "top"),
            (-1, 1, "right", "bottom"), (-1, -1, "right", "top")]
    for i in sorted(range(len(xs)), key=lambda i: (not top[i], -crowd[i])):
        style = dict(fontsize=8.5 if top[i] else 7.5, color="#111" if top[i] else "#777",
                     weight="bold" if top[i] else "normal")
        for r, (ux, uy, ha, va) in ((r, d) for r in (4, 10, 18, 28, 40) for d in dirs):
            at = dict(xy=(xs[i], ys[i]), xytext=(r * ux, r * uy), textcoords="offset points", ha=ha, va=va)
            t = ax.annotate(labels[i], **at, **style)
            box = t.get_window_extent(renderer).expanded(1.03, 1.08)  # text only, before any leader line
            t.remove()
            if frame.contains(box.x0, box.y0) and frame.contains(box.x1, box.y1) \
                    and not any(box.overlaps(b) for b in taken):
                lead = None if r == 4 and not (ux and uy) else \
                    dict(arrowstyle="-", color="#c4c8ce", lw=0.5, shrinkA=1, shrinkB=3)
                ax.annotate(labels[i], **at, **style, arrowprops=lead)
                taken.append(box)
                break
        else:
            raise RuntimeError(f"no room to label {labels[i]}")


def draw_cost_scatter(mt) -> None:
    top = np.arange(len(mt)) < HIGHLIGHT
    cost, rate = mt["mean cost (USD)"].to_numpy(), mt["pass rate"].to_numpy() * 100
    fig, ax = plt.subplots(figsize=HALF)
    ax.scatter(cost[~top], rate[~top], s=18, color=MUTED, zorder=3)
    ax.scatter(cost[top], rate[top], s=34, color=ACCENT, zorder=4)
    ax.grid(color="#eee", zorder=0)
    tidy(ax)
    ax.set_xscale("log")
    ax.set_xlim(0.08, 60)
    dollar_ticks(ax.xaxis, [0.1, 0.3, 1, 3, 10, 30])
    ax.set_ylim(0, 106)
    ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("Pass rate vs. API cost per attempt", color="#111", fontsize=9.5, loc="left")
    ax.set_xlabel("API cost per attempt (log scale)", color="#777")
    fig.subplots_adjust(left=0.11, right=0.98, top=0.93, bottom=0.1)
    label_points(fig, ax, cost, rate, list(mt.model), top)
    fig.savefig(ROOT / "figures" / "cost_vs_pass_rate.png", dpi=200)


def draw_time_and_cost(mt) -> None:
    y = np.arange(len(mt))
    top = y < HIGHLIGHT
    minutes, per_pass = mt["mean minutes"].to_numpy(), mt["cost per pass (USD)"].to_numpy()
    colors = [ACCENT if t else MUTED for t in top]
    fig, (a, b) = plt.subplots(1, 2, figsize=HALF, sharey=True, gridspec_kw={"wspace": 0.16})
    a.barh(y, minutes, height=0.68, color=colors)
    a.axvline(120, color="#c44", lw=0.8, ls="--", zorder=0)  # the two-hour limit
    a.set_xlim(0, 124)
    a.set_xticks([0, 60, 120], ["0", "1 h", "2 h"])
    a.get_xticklabels()[-1].set_horizontalalignment("right")
    a.set_title("Minutes per attempt", color="#111", fontsize=9.5, loc="left")
    b.barh(y, per_pass, height=0.68, color=colors)
    b.set_xlim(0, 52)  # linear, so bar length is proportional to cost; room right of the longest bar for its label
    b.set_xticks([0, 20, 40], ["$0", "$20", "$40"])
    b.set_title("Cost per passing design", color="#111", fontsize=9.5, loc="left")
    for i in y:
        a.text(minutes[i] - 2, i, f"{minutes[i]:.0f}", va="center", ha="right", fontsize=7, color="white")
        b.text(per_pass[i] + 0.8, i, f"${per_pass[i]:.2f}", va="center", fontsize=7, color="#111" if top[i] else "#777")
    tidy(a)
    tidy(b)
    a.set_yticks(y, [f"{m}  {p:.0%}" for m, p in zip(mt.model, mt["pass rate"])], fontsize=7.5)
    for label, t in zip(a.get_yticklabels(), top):
        label.set_color("#111" if t else "#777")
        label.set_weight("bold" if t else "normal")
    a.set_ylim(len(mt) - 0.5, -0.6)
    fig.subplots_adjust(left=0.37, right=0.98, top=0.93, bottom=0.06)
    fig.savefig(ROOT / "figures" / "time_and_cost_by_model.png", dpi=200)


def write_time_and_cost(mt) -> None:
    def row(slug):
        return mt.loc[slug]

    astra, opus, deepseek = row("gpt-6-astra-thinking-max"), row("claude-opus-5-5-max"), row("deepseek-v4-1-flash-1017-max")
    lines = [HEADING, "",
             "Each attempt had at most two hours. Costs are API list prices applied to the tokens each attempt used, computed",
             "as on the [leaderboard](https://analog-design-bench.tokenzhang.com). A passing design costs "
             f"${astra['cost per pass (USD)']:.2f} from GPT-6 Astra",
             f"and ${opus['cost per pass (USD)']:.2f} from Claude Opus 5.5, less than one hour of an analog engineer's time. "
             f"DeepSeek V4.1 Flash 1017 passes {deepseek['pass rate']:.0%}",
             f"of its attempts for ${deepseek['cost per pass (USD)']:.2f} per passing design. The "
             "[notebook](analog_design_bench.ipynb) lists the exact",
             "numbers for every model.", "",
             '<p align="center">',
             '  <img src="figures/cost_vs_pass_rate.png" width="49%" alt="Pass rate against API cost per attempt, '
             'one point per model">',
             '  <img src="figures/time_and_cost_by_model.png" width="49%" alt="Minutes per attempt and API cost per '
             'passing design for each model">',
             "</p>", "", ""]
    readme = ROOT / "README.md"
    text = readme.read_text()
    start = text.index(HEADING)
    end = text.index("\n## ", start + 1) + 1
    readme.write_text(text[:start] + "\n".join(lines) + text[end:])


if __name__ == "__main__":
    main()
