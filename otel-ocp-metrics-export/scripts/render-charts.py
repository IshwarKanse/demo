#!/usr/bin/env python3
"""Render the benchmark graphs from the CSV files written by scripts/export-series.sh.

usage: .venv/bin/python scripts/render-charts.py <results dir>   (e.g. results/2026-10-20)

Reads <results dir>/runs.json and <results dir>/raw/<slug>/<metric>.csv, writes PNGs to
<results dir>/charts/ and a summary table to <results dir>/summary.md. Every number in a chart
comes from a committed CSV. One y axis per panel, thin marks, labels in text colours.
"""
import csv, json, os, sys
from collections import defaultdict
from datetime import datetime, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]  # fixed categorical order
TEXT, MUTED, SURFACE, GRID = "#0b0b0b", "#52514e", "#fcfcfb", "#e6e5e1"
MiB = 1 / 1048576

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT, "xtick.color": MUTED, "ytick.color": MUTED, "text.color": TEXT,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "legend.frameon": False, "lines.linewidth": 2,
    "axes.titleweight": "normal", "axes.titlesize": 11, "figure.dpi": 150,
})


def load(dirpath, slug, metric):
    """Return {series_label: [(datetime, value), ...]} for one metric of one run."""
    f = os.path.join(dirpath, "raw", slug, metric + ".csv")
    out = defaultdict(list)
    if not os.path.exists(f):
        return out
    with open(f) as fh:
        for row in csv.DictReader(fh):
            out[row["series"]].append((datetime.fromtimestamp(int(row["ts"]), timezone.utc), float(row["value"])))
    return out


def total(dirpath, slug, metric):
    """Sum all series of a metric per timestamp -> [(datetime, value)]."""
    acc = defaultdict(float)
    for pts in load(dirpath, slug, metric).values():
        for t, v in pts:
            acc[t] += v
    return sorted(acc.items())


def stats(points):
    vals = sorted(v for _, v in points)
    if not vals:
        return (0.0, 0.0, 0.0)
    n = len(vals)
    return (sum(vals) / n, vals[int(0.95 * (n - 1))], vals[-1])


def steady_rows(dirpath, runs):
    rows = []
    for r in runs:
        if r["kind"] not in ("steady", "baseline"):
            continue
        s = r["slug"]
        samples = stats(total(dirpath, s, "receiver_accepted_points_s"))[0]
        # series per replica of each instance: platform (2 replicas) plus user workload (2 replicas)
        series = sum(stats(total(dirpath, s, m))[0] / 2 for m in ("prometheus_head_series", "uwm_head_series") if total(dirpath, s, m))
        rows.append({
            "run": r, "samples_s": samples, "head_series_per_replica": series,
            "cpu": stats(total(dirpath, s, "collector_cpu_cores")),
            "wss": tuple(x * MiB for x in stats(total(dirpath, s, "collector_wss_bytes"))),
            "rss": tuple(x * MiB for x in stats(total(dirpath, s, "collector_rss_bytes"))),
            "pcpu": stats(total(dirpath, s, "prometheus_cpu_cores")),
            "pwss": tuple(x * MiB for x in stats(total(dirpath, s, "prometheus_wss_bytes"))),
            "ucpu": stats(total(dirpath, s, "uwm_cpu_cores")),
            "uwss": tuple(x * MiB for x in stats(total(dirpath, s, "uwm_wss_bytes"))),
            "pending": stats(total(dirpath, s, "rw_pending_samples"))[2],
            "failed": stats(total(dirpath, s, "rw_failed_samples_s"))[2],
            "retried": stats(total(dirpath, s, "rw_retried_samples_s"))[2],
        })
    return rows


def label_point(ax, x, y, text, dy=6):
    ax.annotate(text, (x, y), textcoords="offset points", xytext=(0, dy), ha="center", fontsize=8, color=MUTED)


def chart_cpu_vs_samples(dirpath, rows, outdir):
    rows = [r for r in rows if r["run"]["kind"] == "steady"]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    by_rep = defaultdict(list)
    for r in rows:
        by_rep[r["run"]["collector_replicas"]].append(r)
    for i, (rep, rs) in enumerate(sorted(by_rep.items())):
        rs.sort(key=lambda r: r["samples_s"])
        xs = [r["samples_s"] / 1000 for r in rs]; ys = [r["cpu"][0] for r in rs]
        ax.plot(xs, ys, marker="o", markersize=5, color=SERIES[i], label=f"{rep} collector replica{'s' if rep > 1 else ''} (all pods)")
        prev_x, flip = None, False
        for x, y in zip(xs, ys):
            # alternate the label side when two points sit within 5 % of each other on the x axis
            flip = (prev_x is not None and abs(x - prev_x) < 0.05 * max(xs)) and not flip
            label_point(ax, x, y, f"{y:.2f}", dy=-14 if flip else 6)
            prev_x = x
    ax.set_xlabel("samples per second into the collector (thousands)")
    ax.set_ylabel("CPU cores, average over the window")
    ax.set_ylim(bottom=0)
    ax.set_title("Collector CPU against the remote write rate")
    if len(by_rep) > 1:
        ax.legend(loc="upper left")
    else:
        ax.set_title(f"Collector CPU against the remote write rate, {list(by_rep)[0]} replica")
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "collector_cpu_vs_samples.png")); plt.close(fig)


def chart_memory(dirpath, rows, outdir):
    rows = [r for r in rows if r["run"]["kind"] == "steady" and r["run"]["collector_replicas"] == 1]
    if not rows:
        return
    rows.sort(key=lambda r: r["samples_s"])
    # the series panel uses the series tiers only: after a tier the stale series stay in the Prometheus
    # head until the next truncation, so the head series count of a later rate tier is not its own
    series_rows = sorted([r for r in rows if r["run"]["label"].startswith("series:")], key=lambda r: r["head_series_per_replica"]) or rows
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, key, xlabel, rs in ((axes[0], "samples_s", "samples per second (thousands)", rows),
                                (axes[1], "head_series_per_replica", "active series per replica (thousands)", series_rows)):
        xs = [r[key] / 1000 for r in rs]
        ax.plot(xs, [r["wss"][0] for r in rs], marker="o", markersize=5, color=SERIES[0], label="working set, average")
        ax.plot(xs, [r["wss"][2] for r in rs], marker="o", markersize=5, color=SERIES[1], label="working set, max")
        ax.plot(xs, [r["rss"][2] for r in rs], marker="o", markersize=5, color=SERIES[2], label="RSS, max")
        ax.set_xlabel(xlabel); ax.set_ylim(bottom=0)
    axes[0].set_ylabel("MiB, one collector replica"); axes[0].legend(loc="upper left")
    axes[1].set_xlabel("active series per replica, platform plus user workload (thousands)")
    fig.suptitle("Collector memory against the remote write rate and the series count", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "collector_memory.png")); plt.close(fig)


def chart_prometheus(dirpath, rows, outdir):
    rows = [r for r in rows if r["run"]["collector_replicas"] <= 1 or r["run"]["kind"] == "baseline"]
    if not rows:
        return
    rows.sort(key=lambda r: (r["run"]["kind"] != "baseline", r["samples_s"]))
    def short(run):
        lab = run["label"].split(": ", 1)[-1].replace(", 1 replica", "").replace(" load pods", " pods").replace(" interval", "")
        return lab
    names = [("no remote write" if r["run"]["kind"] == "baseline" else f"{r['samples_s']/1000:.0f}k/s, {short(r['run'])}") for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, key, ylabel in ((axes[0], "pcpu", "CPU cores, both replicas, average"), (axes[1], "pwss", "working set MiB, both replicas, average")):
        ys = [r[key][0] for r in rows]
        colors = [SERIES[2] if r["run"]["kind"] == "baseline" else SERIES[0] for r in rows]
        bars = ax.bar(names, ys, color=colors, width=0.6)
        for b, y in zip(bars, ys):
            label_point(ax, b.get_x() + b.get_width() / 2, y, f"{y:.2f}" if key == "pcpu" else f"{y:.0f}")
        ax.set_ylabel(ylabel); ax.set_ylim(0, max(ys) * 1.2 if ys else 1); ax.tick_params(axis="x", labelrotation=35, labelsize=8)
    fig.suptitle("Platform Prometheus cost with remote write v2 (green: baseline without remote write)", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "prometheus_cost.png")); plt.close(fig)


def timeline(dirpath, run, outdir, panels, filename, title, markers=None):
    s = run["slug"]
    fig, axes = plt.subplots(len(panels), 1, figsize=(9, 2.2 * len(panels)), sharex=True)
    if len(panels) == 1:
        axes = [axes]
    for ax, (ylabel, items) in zip(axes, panels):
        for i, (metric, lab, scale) in enumerate(items):
            pts = total(dirpath, s, metric)
            if not pts:
                continue
            ax.plot([t for t, _ in pts], [v * scale for _, v in pts], color=SERIES[i], label=lab)
        ax.set_ylabel(ylabel); ax.set_ylim(bottom=0)
        if len(items) > 1:
            ax.legend(loc="upper left", fontsize=8)
        for t, text in (markers or []):
            ax.axvline(t, color=MUTED, linewidth=1, linestyle="--")
        if markers:
            for t, text in markers:
                axes[0].annotate(text, (t, axes[0].get_ylim()[1]), textcoords="offset points", xytext=(3, -10), fontsize=8, color=MUTED)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel("time (UTC)")
    fig.suptitle(title, color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, filename)); plt.close(fig)


def chart_outage(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "outage"]:
        timeline(dirpath, r, outdir, [
            ("queue items", [("exporter_queue_items", "exporter queue", 1)]),
            ("collector MiB", [("collector_wss_bytes", "working set", MiB), ("collector_rss_bytes", "RSS", MiB)]),
            ("points/s", [("receiver_accepted_points_s", "accepted", 1), ("receiver_refused_points_s", "refused", 1), ("exporter_sent_points_s", "exported", 1)]),
            ("Prometheus samples", [("rw_pending_samples", "pending", 1)]),
            ("Prometheus samples/s", [("rw_retried_samples_s", "retried", 1), ("rw_failed_samples_s", "failed", 1)]),
        ], f"outage_{r['slug']}.png", f"Backend outage and recovery: {r['label']}")


def compaction_markers(dirpath, run):
    """One marker per compaction; compactions of both replicas within 2 minutes share a label."""
    raw = []
    for pod, pts in load(dirpath, run["slug"], "prometheus_compactions_total").items():
        prev = None
        for t, v in pts:
            if prev is not None and v > prev:
                raw.append((t, pod.split("pod=")[-1].replace("prometheus-", "")))
            prev = v
    raw.sort()
    marks = []
    for t, pod in raw:
        if marks and (t - marks[-1][0]).total_seconds() < 120:
            marks[-1] = (marks[-1][0], marks[-1][1] + ", " + pod)
        else:
            marks.append((t, "compaction " + pod))
    return marks


def chart_compaction(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "compaction"]:
        timeline(dirpath, r, outdir, [
            ("Prometheus CPU cores", [("prometheus_cpu_cores", "both replicas", 1)]),
            ("Prometheus MiB", [("prometheus_wss_bytes", "working set, both replicas", MiB)]),
            ("remote write samples/s", [("rw_samples_s", "samples/s", 1)]),
            ("shards", [("rw_shards", "remote write shards", 1)]),
            ("collector MiB", [("collector_wss_bytes", "working set", MiB)]),
        ], f"compaction_{r['slug']}.png", f"Steady state across TSDB compactions: {r['label']}", markers=compaction_markers(dirpath, r))


def chart_churn(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "churn"]:
        timeline(dirpath, r, outdir, [
            ("thousand series", [("uwm_head_series", "user workload Prometheus, both replicas", 0.001), ("prometheus_head_series", "platform Prometheus, both replicas", 0.001)]),
            ("thousand chunks", [("uwm_head_chunks", "user workload Prometheus", 0.001), ("prometheus_head_chunks", "platform Prometheus", 0.001)]),
            ("series created/s", [("uwm_series_created_s", "user workload Prometheus", 1), ("prometheus_series_created_s", "platform Prometheus", 1)]),
            ("Prometheus MiB", [("uwm_wss_bytes", "user workload, both replicas", MiB), ("prometheus_wss_bytes", "platform, both replicas", MiB)]),
            ("Prometheus CPU cores", [("uwm_cpu_cores", "user workload, both replicas", 1), ("prometheus_cpu_cores", "platform, both replicas", 1)]),
            ("remote write samples/s", [("rw_samples_s", "all instances", 1)]),
        ], f"churn_{r['slug']}.png", f"Series churn: {r['label']}")


def summary(dirpath, rows, runs):
    lines = ["| run | kind | collector replicas | samples/s | series per replica | collector CPU avg / p95 | working set MiB avg / max | RSS MiB max | platform Prometheus CPU avg | platform Prometheus WSS MiB avg | UWM Prometheus CPU avg | UWM Prometheus WSS MiB avg | pending max | failed/s max | retried/s max | restarts | pods | load pods |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        run = r["run"]
        lines.append(f"| {run['label']} | {run['kind']} | {run['collector_replicas']} | {r['samples_s']:,.0f} | {r['head_series_per_replica']:,.0f} | {r['cpu'][0]:.2f} / {r['cpu'][1]:.2f} | {r['wss'][0]:.0f} / {r['wss'][2]:.0f} | {r['rss'][2]:.0f} | {r['pcpu'][0]:.2f} | {r['pwss'][0]:.0f} | {r['ucpu'][0]:.2f} | {r['uwss'][0]:.0f} | {r['pending']:,.0f} | {r['failed']:.0f} | {r['retried']:.0f} | {run['collector_restarts']} | {run['cluster']['pods_running']} | {run['load_pods']} |")
    cl = runs[0]["cluster"] if runs else {}
    head = [f"Cluster: OpenShift {cl.get('version')} on {cl.get('platform')}, {cl.get('nodes')} nodes ({cl.get('workers')} workers, allocatable {cl.get('worker_allocatable')} each).", ""]
    with open(os.path.join(dirpath, "summary.md"), "w") as f:
        f.write("\n".join(head + lines) + "\n")


def main():
    dirpath = sys.argv[1]
    runs = json.load(open(os.path.join(dirpath, "runs.json")))
    outdir = os.path.join(dirpath, "charts"); os.makedirs(outdir, exist_ok=True)
    rows = steady_rows(dirpath, runs)
    chart_cpu_vs_samples(dirpath, rows, outdir)
    chart_memory(dirpath, rows, outdir)
    chart_prometheus(dirpath, rows, outdir)
    chart_outage(dirpath, runs, outdir)
    chart_compaction(dirpath, runs, outdir)
    chart_churn(dirpath, runs, outdir)
    summary(dirpath, rows, runs)
    print("charts:", sorted(os.listdir(outdir)))


if __name__ == "__main__":
    main()
