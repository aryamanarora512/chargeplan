"""Report charts (static SVG), drawn to one spec in a light and a dark version.

The spec: 2px lines, 8px markers with a ring in the background color, solid
hairline gridlines, no box around the plot, text in ink colors (never a series
color), a legend whenever there are 2+ series, and the SAME color for the same
policy in every chart. Dark mode uses its own color steps, checked for contrast
and color-blind separation against the dark background (not an automatic invert).
"""

import matplotlib

matplotlib.use("Agg")  # draw to files; no window needed

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, PercentFormatter

from .estimate import POLICIES, POLICY_LABELS, Estimate, Replay

THEMES = {
    "light": {
        "surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
        "grid": "#e1e0d9", "axis": "#c3c2b7",
        "series": {"optimized": "#2a78d6", "arrival": "#eb6834", "timer": "#1baf7a"},
    },
    "dark": {
        "surface": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "muted": "#898781",
        "grid": "#2c2c2a", "axis": "#383835",
        "series": {"optimized": "#3987e5", "arrival": "#d95926", "timer": "#199e70"},
    },
}
LINE = 1.5  # points; about 2px
HAIRLINE = 0.75  # about 1px
MARKER = 6.5  # points across; about 8-9px
plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "svg.fonttype": "path",  # embed glyph shapes so the SVG looks the same everywhere
        "axes.titlesize": 10,
    }
)


def _style_axes(ax, th, *, ygrid=True):
    ax.set_facecolor(th["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(th["axis"])
    ax.spines["bottom"].set_linewidth(HAIRLINE)
    ax.tick_params(colors=th["muted"], labelcolor=th["muted"], labelsize=8.5, length=0, pad=6)
    if ygrid:
        ax.grid(axis="y", color=th["grid"], linewidth=HAIRLINE, linestyle="-")
    ax.set_axisbelow(True)


def _header(fig, th, title, subtitle, legend_handles=None):
    fig.patch.set_facecolor(th["surface"])
    fig.text(0.012, 0.975, title, color=th["ink"], fontsize=13, fontweight="bold", va="top")
    fig.text(0.012, 0.915, subtitle, color=th["ink2"], fontsize=9.5, va="top")
    if legend_handles:
        leg = fig.legend(
            handles=legend_handles, loc="upper left", bbox_to_anchor=(0.006, 0.865), ncol=len(legend_handles),
            frameon=False, fontsize=9, handlelength=1.8, columnspacing=1.6, labelcolor=th["ink2"],
        )
        leg.set_in_layout(False)


def _key(th, policy, marker=False):
    color = th["series"][policy]
    return Line2D(
        [], [], color=color, linewidth=LINE, solid_capstyle="round", label=POLICY_LABELS[policy],
        marker="o" if marker else None, markersize=MARKER, markerfacecolor=color,
        markeredgecolor=th["surface"], markeredgewidth=1.5,
    )


def power_profile(rep: Replay, *, site_limit_kw: float, title_detail: str, theme: str = "light"):
    """Average site charging power per 30-minute slot, with the tariff as a strip below."""
    th = THEMES[theme]
    n = len(rep.slot_clock)
    x = np.arange(n + 1)  # slot edges; values are steps over each slot
    fig, (ax, ax_p) = plt.subplots(2, 1, figsize=(9, 5.2), sharex=True, gridspec_kw={"height_ratios": [4, 1], "hspace": 0.12})
    fig.subplots_adjust(left=0.07, right=0.98, top=0.79, bottom=0.08)
    for a in (ax, ax_p):
        _style_axes(a, th)

    for policy in ("arrival", "timer", "optimized"):  # optimized drawn last, on top
        mean_kw = rep.profiles[policy].mean(axis=0)
        ax.step(x, np.append(mean_kw, mean_kw[-1]), where="post", color=th["series"][policy],
                linewidth=LINE, solid_joinstyle="round", solid_capstyle="round")
    ax.axhline(site_limit_kw, color=th["ink2"], linewidth=HAIRLINE, linestyle=(0, (4, 3)))  # a real limit, so dashed
    ax.text(n, site_limit_kw, f"Site limit {site_limit_kw:g} kW", color=th["muted"], fontsize=8.5, ha="right", va="bottom")
    ax.set_ylim(0, site_limit_kw * 1.15)
    ax.set_ylabel("kW", color=th["muted"], fontsize=8.5, rotation=0, ha="right", va="center")

    prices = np.array(rep.slot_price)
    ax_p.step(x, np.append(prices, prices[-1]), where="post", color=th["ink2"], linewidth=LINE)
    ax_p.set_ylim(0, prices.max() * 1.45)
    ax_p.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:.2f}"))
    ax_p.set_yticks([prices.min(), prices.max()])
    ax_p.set_ylabel("$/kWh", color=th["muted"], fontsize=8.5, rotation=0, ha="right", va="center")
    ticks = list(range(0, n + 1, 4))
    ax_p.set_xticks(ticks, [rep.slot_clock[i].strftime("%H:%M") if i < n else _end_label(rep) for i in ticks])
    ax_p.set_xlim(0, n)

    nights = rep.profiles["optimized"].shape[0]
    _header(fig, th, "Average charging power across the night", f"{nights} nights · {title_detail}",
            [_key(th, p) for p in POLICIES])
    return fig


def _end_label(rep: Replay) -> str:
    last = rep.slot_clock[-1]
    minutes = (last.hour * 60 + last.minute + 30) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def readiness_sizing(sweep, *, title_detail: str, theme: str = "light"):
    """Share of nights every vehicle is ready, against the EV charging allowance."""
    th = THEMES[theme]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    fig.subplots_adjust(left=0.07, right=0.98, top=0.74, bottom=0.12)
    _style_axes(ax, th)
    allowances = sorted(sweep["allowance_kw"].unique())
    for policy in ("arrival", "timer", "optimized"):
        part = sweep[sweep["policy"] == policy].sort_values("allowance_kw")
        ax.plot(part["allowance_kw"], part["share_ready"], color=th["series"][policy], linewidth=LINE,
                marker="o", markersize=MARKER, markerfacecolor=th["series"][policy],
                markeredgecolor=th["surface"], markeredgewidth=1.5, solid_capstyle="round", solid_joinstyle="round")
    ax.set_ylim(0, 1.06)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticks(allowances, [f"{a:g}" for a in allowances])
    ax.set_xlabel("EV charging allowance (kW)", color=th["muted"], fontsize=8.5)

    lines = ["Every night ready from"]
    for policy in POLICIES:
        part = sweep[(sweep["policy"] == policy) & (sweep["share_ready"] >= 1.0)]
        kw = part["allowance_kw"].min()
        lines.append(f"{POLICY_LABELS[policy]}: {'never' if np.isnan(kw) else f'{kw:g} kW'}")
    ax.text(0.985, 0.06, "\n".join(lines), transform=ax.transAxes, ha="right", va="bottom",
            color=th["ink2"], fontsize=8.5, linespacing=1.6)
    _header(fig, th, "Share of nights every van is ready, by charging allowance", title_detail,
            [_key(th, p, marker=True) for p in POLICIES])
    return fig


def savings_estimate(estimates: dict, *, title_detail: str, theme: str = "light"):
    """Dot = estimated annual savings, line = 90% bootstrap interval. One row per
    (tariff, baseline). `estimates` maps tariff name -> {baseline: Estimate | None}."""
    th = THEMES[theme]
    rows = [(tariff, b) for tariff, by_base in estimates.items() for b in ("arrival", "timer")]
    gap = 0.8  # extra space between tariff groups
    ys, y, last = [], 0.0, None
    for tariff, _ in rows:
        if last is not None and tariff != last:
            y += gap
        ys.append(y)
        y += 1
        last = tariff
    fig, ax = plt.subplots(figsize=(9, 1.6 + 0.55 * (len(rows) + gap * (len(estimates) - 1))))
    fig.subplots_adjust(left=0.24, right=0.98, top=0.76, bottom=0.12)
    _style_axes(ax, th, ygrid=False)
    ax.grid(axis="x", color=th["grid"], linewidth=HAIRLINE)

    highs = [e.high for by in estimates.values() for e in by.values() if e is not None]
    xmax = max(highs + [1.0]) * 1.5  # leave room for the value labels
    for yy, (tariff, base) in zip(ys, rows):
        est: Estimate | None = estimates[tariff][base]
        color = th["series"][base]
        if est is None:
            ax.text(0, yy, "  not comparable (baseline never readied every van)", color=th["muted"], fontsize=8.5, va="center")
            continue
        ax.plot([est.low, est.high], [yy, yy], color=color, linewidth=LINE, solid_capstyle="round")
        ax.plot([est.annual], [yy], marker="o", markersize=MARKER, color=color, markeredgecolor=th["surface"], markeredgewidth=1.5)
        ax.text(max(est.high, est.annual) + xmax * 0.015, yy,
                f"${est.annual:,.0f}/yr   90%: ${est.low:,.0f}–${est.high:,.0f} · {est.nights} nights",
                color=th["ink2"], fontsize=8.5, va="center")
    ax.set_yticks(ys, [("vs " + POLICY_LABELS[b].lower()) for _, b in rows])
    for label in ax.get_yticklabels():
        label.set_color(th["ink2"])
        label.set_fontsize(9)
    group_tops = {}
    for yy, (tariff, _) in zip(ys, rows):
        group_tops.setdefault(tariff, yy)
    for tariff, yy in group_tops.items():
        ax.text(-0.235, yy - 0.6, tariff, transform=ax.get_yaxis_transform(), color=th["ink"], fontsize=9.5,
                fontweight="bold", va="center", ha="left")
    ax.set_ylim(max(ys) + 0.55, -0.9)
    ax.set_xlim(0, xmax)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v / 1000:,.0f}K" if v >= 1000 else f"${v:,.0f}"))
    _header(fig, th, "Estimated annual energy-cost savings of ChargePlan", title_detail,
            [_key(th, "arrival", marker=True), _key(th, "timer", marker=True)])
    return fig


def save(fig, path, theme: str) -> None:
    fig.savefig(path, format="svg", facecolor=THEMES[theme]["surface"], bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
