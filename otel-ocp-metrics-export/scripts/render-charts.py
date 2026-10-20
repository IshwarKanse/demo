#!/usr/bin/env python3
"""Render the benchmark graphs from the CSV files written by scripts/export-series.sh.

usage: .venv/bin/python scripts/render-charts.py <results dir>   (e.g. results/2026-10-20, or
       collector-only/results/2026-10-20 for the option 2 runs exported with PROFILE=collector-only)

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
        if marks and (t - marks[-1][0]).total_seconds() < 300:
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



# ---------------------------------------------------------------------------------------------------------
# collector-only profile (option 2: collector-only/, runs.json entries with "profile": "collector-only")
# ---------------------------------------------------------------------------------------------------------

def col_series(dirpath, slug, metric, col):
    """[(datetime, value)] of one collector (node | cluster) for a metric split by the collector label."""
    return load(dirpath, slug, metric).get(f"collector={col}", [])


def co_rows(dirpath, runs):
    rows = []
    for r in runs:
        if r["kind"] not in ("steady", "rate", "long"):
            continue
        s = r["slug"]; row = {"run": r, "pods": r["cluster"]["pods_running"]}
        for c in ("cluster", "node"):
            row[c] = {
                "cpu": stats(col_series(dirpath, s, "collector_cpu_cores", c)),
                "cpu_pod": stats(col_series(dirpath, s, "collector_cpu_cores_max_pod", c)),
                "wss": tuple(x * MiB for x in stats(col_series(dirpath, s, "collector_wss_bytes", c))),
                "wss_pod": tuple(x * MiB for x in stats(col_series(dirpath, s, "collector_wss_bytes_max_pod", c))),
                "rss": tuple(x * MiB for x in stats(col_series(dirpath, s, "collector_rss_bytes", c))),
                "points": stats(col_series(dirpath, s, "receiver_accepted_points_s", c)),
                "refused": stats(col_series(dirpath, s, "receiver_refused_points_s", c))[2],
                "queue": stats(col_series(dirpath, s, "exporter_queue_items", c))[2],
                "enqueue_failed": stats(col_series(dirpath, s, "exporter_enqueue_failed_points_s", c))[2],
                "ml_refused": stats(col_series(dirpath, s, "memory_limiter_refused_points_s", c))[2],
                "by_receiver": {k.split("receiver=")[-1]: stats(v)[0] for k, v in load(dirpath, s, "receiver_accepted_points_s_by_receiver").items() if f"collector={c}" in k},
            }
        row["proxy_req"] = stats(total(dirpath, s, "apiserver_node_proxy_req_s"))[0]
        row["apiserver_cpu"] = stats(total(dirpath, s, "apiserver_cpu_cores"))[0]
        row["apiserver_wss"] = stats(total(dirpath, s, "apiserver_wss_bytes"))[0] * MiB
        row["ta_cpu"] = stats(total(dirpath, s, "ta_cpu_cores"))[0]
        row["ta_wss"] = stats(total(dirpath, s, "ta_wss_bytes"))[0] * MiB
        row["option1_rw"] = stats(total(dirpath, s, "option1_rw_samples_s"))[0]
        row["head_series"] = stats(total(dirpath, s, "prometheus_head_series"))[0] / 2
        rows.append(row)
    return rows


def co_kind(row):
    """deployment tier | scale-out | documented shape | rate, from the run label prefix."""
    return row["run"]["label"].split(":", 1)[0]


def co_point_label(row):
    r = row["run"]
    if r["kind"] == "rate":
        return r["config"].split(" interval")[0] + " interval"
    if co_kind(row) == "scale-out":
        return "2 replicas + TA"
    if co_kind(row) == "documented shape":
        return "no kubelet jobs"
    return None


def co_scatter(ax, rows, xkey, ykey, color, label, marker="o", annotate=None):
    rows = sorted(rows, key=xkey)
    xs = [xkey(r) for r in rows]; ys = [ykey(r) for r in rows]
    ax.plot(xs, ys, marker=marker, markersize=6, color=color, label=label, linewidth=2 if len(rows) > 1 else 0)
    for r, x, y in zip(rows, xs, ys):
        text = annotate(r, y) if annotate else None
        if text:
            label_point(ax, x, y, text)


def co_split(rows):
    tiers = [r for r in rows if co_kind(r) == "tiers"]
    others = [r for r in rows if co_kind(r) != "tiers" and r["run"]["kind"] != "long"]
    return tiers, others


def co_chart_cpu(dirpath, rows, outdir):
    tiers, others = co_split(rows)
    if not tiers:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["cluster"]["cpu"][0], SERIES[0], "deployment, 1 replica, average", annotate=lambda r, y: f"{y:.2f}")
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["cluster"]["cpu"][1], SERIES[1], "deployment, 1 replica, p95")
    for i, r in enumerate(others):
        co_scatter(ax, [r], lambda r: r["pods"], lambda r: r["cluster"]["cpu"][0], SERIES[2 + i % 4], co_point_label(r) + ", average", marker="D", annotate=lambda r, y: f"{y:.2f}")
    ax.set_xlabel("pods running in the cluster"); ax.set_ylabel("CPU cores, all replicas"); ax.set_ylim(bottom=0)
    ax.set_title("Cluster collector"); ax.legend(fontsize=8, loc="upper left")
    ax = axes[1]
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["node"]["cpu_pod"][0], SERIES[0], "busiest node, average", annotate=lambda r, y: f"{y:.3f}")
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["node"]["cpu"][0], SERIES[1], "all nodes together, average", annotate=lambda r, y: f"{y:.3f}")
    ax.set_xlabel("pods running in the cluster"); ax.set_ylabel("CPU cores"); ax.set_ylim(bottom=0)
    ax.set_title("Node collector (one pod per node)"); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Collector CPU against the number of pods", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "co_cpu_vs_pods.png")); plt.close(fig)


def co_chart_memory(dirpath, rows, outdir):
    tiers, others = co_split(rows)
    if not tiers:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ax = axes[0]
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["cluster"]["wss"][0], SERIES[0], "working set, average", annotate=lambda r, y: f"{y:.0f}")
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["cluster"]["wss"][2], SERIES[1], "working set, max")
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["cluster"]["rss"][2], SERIES[2], "RSS, max")
    # the interval tiers barely move the memory and are in the CPU-against-points chart; the three colours left
    # after the tier lines go to the shape variants
    for i, r in enumerate([r for r in others if r["run"]["kind"] != "rate"]):
        co_scatter(ax, [r], lambda r: r["pods"], lambda r: r["cluster"]["wss"][0], SERIES[3 + i % 3], co_point_label(r) + ", working set avg", marker="D", annotate=lambda r, y: f"{y:.0f}")
    ax.set_xlabel("pods running in the cluster"); ax.set_ylabel("MiB, all replicas together"); ax.set_ylim(bottom=0)
    ax.set_title("Cluster collector"); ax.legend(fontsize=8, loc="upper left")
    ax = axes[1]
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["node"]["wss_pod"][0], SERIES[0], "busiest node, working set avg", annotate=lambda r, y: f"{y:.0f}")
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["node"]["wss_pod"][2], SERIES[1], "busiest node, working set max")
    co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r["node"]["rss"][2], SERIES[2], "busiest node, RSS max")
    ax.set_xlabel("pods running in the cluster"); ax.set_ylabel("MiB, one node collector pod"); ax.set_ylim(bottom=0)
    ax.set_title("Node collector (one pod per node)"); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Collector memory against the number of pods", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "co_memory_vs_pods.png")); plt.close(fig)


def co_chart_points(dirpath, rows, outdir):
    tiers, _ = co_split(rows)
    if not tiers:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, c, title in ((axes[0], "cluster", "Cluster collector"), (axes[1], "node", "Node collector, all nodes together")):
        receivers = sorted({k for r in tiers for k in r[c]["by_receiver"]})
        for i, rec in enumerate(receivers):
            co_scatter(ax, tiers, lambda r: r["pods"], lambda r, rec=rec: r[c]["by_receiver"].get(rec, 0) / 1000, SERIES[i], rec)
        co_scatter(ax, tiers, lambda r: r["pods"], lambda r: r[c]["points"][0] / 1000, SERIES[5], "total", annotate=lambda r, y: f"{y:.1f}k")
        ax.set_xlabel("pods running in the cluster"); ax.set_ylabel("thousand data points per second"); ax.set_ylim(bottom=0)
        ax.set_title(title); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Data points per second received, by receiver (a histogram or summary counts as one point)", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "co_points_vs_pods.png")); plt.close(fig)


def co_chart_cpu_vs_points(dirpath, rows, outdir):
    rows = [r for r in rows if r["run"]["kind"] in ("steady", "rate")]
    if len(rows) < 2:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for ax, c, title, ykey in ((axes[0], "cluster", "Cluster collector, all replicas", lambda r: r["cluster"]["cpu"][0]),
                               (axes[1], "node", "Node collector, busiest node", lambda r: r["node"]["cpu_pod"][0])):
        xkey = (lambda r: r[c]["points"][0] / 1000) if c == "cluster" else (lambda r: r["node"]["points"][0] / 1000 / max(r["run"]["node_collector_pods"], 1))
        tiers = [r for r in rows if co_kind(r) == "tiers"]
        rates = [r for r in rows if r["run"]["kind"] == "rate"]
        others = [r for r in rows if co_kind(r) not in ("tiers",) and r["run"]["kind"] != "rate"]
        co_scatter(ax, tiers, xkey, ykey, SERIES[0], "pod tiers, 30 s interval", annotate=lambda r, y: f"{r['pods']} pods")
        co_scatter(ax, rates, xkey, ykey, SERIES[1], "interval tiers, same pods", marker="s", annotate=lambda r, y: co_point_label(r))
        for i, r in enumerate(others):
            co_scatter(ax, [r], xkey, ykey, SERIES[2 + i % 4], co_point_label(r), marker="D")
        ax.set_xlabel("thousand data points per second" + (" per node" if c == "node" else "")); ax.set_ylabel("CPU cores, average"); ax.set_ylim(bottom=0)
        ax.set_title(title); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Collector CPU against the data point rate (pods vary the series, the interval varies the rate)", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "co_cpu_vs_points.png")); plt.close(fig)


def co_chart_control_plane(dirpath, rows, outdir):
    tiers, others = co_split(rows)
    if not tiers:
        return
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, key, ylabel, fmt in ((axes[0], "proxy_req", "API server node proxy requests/s", "{:.1f}"),
                                 (axes[1], "apiserver_cpu", "kube-apiserver CPU cores, 3 instances", "{:.2f}"),
                                 (axes[2], "apiserver_wss", "kube-apiserver working set MiB, 3 instances", "{:.0f}")):
        co_scatter(ax, tiers, lambda r: r["pods"], lambda r, key=key: r[key], SERIES[0], "pod tiers", annotate=lambda r, y, fmt=fmt: fmt.format(y))
        for i, r in enumerate(others):
            co_scatter(ax, [r], lambda r: r["pods"], lambda r, key=key: r[key], SERIES[2 + i % 4], co_point_label(r), marker="D", annotate=lambda r, y, fmt=fmt: fmt.format(y))
        ax.set_xlabel("pods running in the cluster"); ax.set_ylabel(ylabel); ax.set_ylim(bottom=0); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Control plane cost: kubelet access through the API server node proxy and kube-apiserver usage per tier", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "co_control_plane.png")); plt.close(fig)


def co_timeline(dirpath, run, outdir, panels, filename, title):
    """timeline() variant for series split by collector: items are (metric, collector or None, label, scale)."""
    s = run["slug"]
    fig, axes = plt.subplots(len(panels), 1, figsize=(9, 2.2 * len(panels)), sharex=True)
    markers = [(datetime.fromtimestamp(m["ts"], timezone.utc), m["name"]) for m in run.get("markers", [])]
    for ax, (ylabel, items) in zip(axes, panels):
        for i, (metric, col, lab, scale) in enumerate(items):
            pts = col_series(dirpath, s, metric, col) if col else total(dirpath, s, metric)
            if not pts:
                continue
            ax.plot([t for t, _ in pts], [v * scale for _, v in pts], color=SERIES[i], label=lab)
        ax.set_ylabel(ylabel); ax.set_ylim(bottom=0)
        if len(items) > 1:
            ax.legend(loc="upper left", fontsize=8)
        for t, _ in markers:
            ax.axvline(t, color=MUTED, linewidth=1, linestyle="--")
    for t, text in markers:
        axes[0].annotate(text, (t, axes[0].get_ylim()[1]), textcoords="offset points", xytext=(3, -10), fontsize=8, color=MUTED)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc))
    axes[-1].set_xlabel("time (UTC)")
    fig.suptitle(title, color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, filename)); plt.close(fig)


def co_chart_outage(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "outage"]:
        co_timeline(dirpath, r, outdir, [
            ("queue items", [("exporter_queue_items", "cluster", "cluster collector", 1), ("exporter_queue_items", "node", "node collectors together", 1)]),
            ("cluster collector MiB", [("collector_wss_bytes", "cluster", "working set", MiB), ("collector_rss_bytes", "cluster", "RSS", MiB)]),
            ("cluster collector points/s", [("receiver_accepted_points_s", "cluster", "accepted", 1), ("receiver_refused_points_s", "cluster", "refused", 1), ("exporter_sent_points_s", "cluster", "exported", 1), ("exporter_enqueue_failed_points_s", "cluster", "enqueue failed", 1)]),
            ("node collectors points/s", [("receiver_accepted_points_s", "node", "accepted", 1), ("receiver_refused_points_s", "node", "refused", 1), ("exporter_sent_points_s", "node", "exported", 1)]),
            ("node collector MiB", [("collector_wss_bytes_max_pod", "node", "working set, busiest node", MiB), ("collector_rss_bytes", "node", "RSS, busiest node", MiB)]),
        ], f"outage_{r['slug']}.png", f"Backend outage and recovery: {r['label']}")


def co_chart_long(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "long"]:
        co_timeline(dirpath, r, outdir, [
            ("pods running", [("cluster_pods_running", None, "pods", 1)]),
            ("cluster collector CPU cores", [("collector_cpu_cores", "cluster", "CPU", 1)]),
            ("cluster collector MiB", [("collector_wss_bytes", "cluster", "working set", MiB), ("collector_rss_bytes", "cluster", "RSS", MiB)]),
            ("cluster collector points/s", [("receiver_accepted_points_s", "cluster", "accepted", 1), ("receiver_refused_points_s", "cluster", "refused", 1)]),
            ("node collector MiB", [("collector_wss_bytes_max_pod", "node", "working set, busiest node", MiB), ("collector_rss_bytes", "node", "RSS, busiest node", MiB)]),
            ("node collectors points/s", [("receiver_accepted_points_s", "node", "accepted, all nodes", 1), ("receiver_refused_points_s", "node", "refused", 1)]),
        ], f"long_{r['slug']}.png", f"Long steady window: {r['label']}")


def co_fit(tiers, key):
    """least-squares slope and intercept of key(row) against the pod count."""
    xs = [r["pods"] for r in tiers]; ys = [key(r) for r in tiers]
    n = len(xs)
    if n < 2:
        return (0.0, ys[0] if ys else 0.0)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    return slope, my - slope * mx


def co_summary(dirpath, rows, runs):
    cl = runs[0]["cluster"] if runs else {}
    tiers = [r for r in rows if co_kind(r) == "tiers"]
    head = [f"Cluster: OpenShift {cl.get('version')} on {cl.get('platform')}, {cl.get('nodes')} nodes ({cl.get('workers')} workers, allocatable {cl.get('worker_allocatable')} each; control plane {cl.get('master_allocatable')} each).",
            f"Collector image: {runs[0].get('collector_image', '')}.", ""]
    if len(tiers) >= 2:
        sw, iw = co_fit(tiers, lambda r: r["cluster"]["wss"][0]); sc, ic = co_fit(tiers, lambda r: r["cluster"]["cpu"][0])
        sp, ip = co_fit(tiers, lambda r: r["cluster"]["points"][0])
        head += [f"Linear fit over the deployment tiers (cluster collector): working set {iw:.0f} MiB + {sw * 1000:.0f} MiB per 1,000 pods, "
                 f"CPU {ic:.2f} cores + {sc * 1000:.2f} cores per 1,000 pods, {ip:,.0f} + {sp * 1000:,.0f} data points/s per 1,000 pods.", ""]
    lines = ["| run | pods running | idle pods | cluster collector: points/s | CPU avg / p95 | WSS MiB avg / max | RSS MiB max | refused/s max | queue max | node collector: points/s all nodes | busiest node CPU avg | busiest node WSS MiB avg / max | RSS MiB max | refused/s max | API server node proxy req/s | kube-apiserver CPU | kube-apiserver WSS MiB | option 1 remote write samples/s | restarts cluster / node |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        run = r["run"]; c = r["cluster"]; n = r["node"]
        lines.append(f"| {run['label']} | {r['pods']} | {run['load_pods']} | {c['points'][0]:,.0f} | {c['cpu'][0]:.2f} / {c['cpu'][1]:.2f} | {c['wss'][0]:.0f} / {c['wss'][2]:.0f} | {c['rss'][2]:.0f} | {c['refused']:.0f} | {c['queue']:,.0f} | {n['points'][0]:,.0f} | {n['cpu_pod'][0]:.3f} | {n['wss_pod'][0]:.0f} / {n['wss_pod'][2]:.0f} | {n['rss'][2]:.0f} | {n['refused']:.0f} | {r['proxy_req']:.1f} | {r['apiserver_cpu']:.2f} | {r['apiserver_wss']:.0f} | {r['option1_rw']:,.0f} | {run['collector_restarts']} / {run.get('node_collector_restarts', 0)} |")
    with open(os.path.join(dirpath, "summary.md"), "w") as f:
        f.write("\n".join(head + lines) + "\n")


def render_collector_only(dirpath, runs, outdir):
    rows = co_rows(dirpath, runs)
    co_chart_cpu(dirpath, rows, outdir)
    co_chart_memory(dirpath, rows, outdir)
    co_chart_points(dirpath, rows, outdir)
    co_chart_cpu_vs_points(dirpath, rows, outdir)
    co_chart_control_plane(dirpath, rows, outdir)
    co_chart_outage(dirpath, runs, outdir)
    co_chart_long(dirpath, runs, outdir)
    co_summary(dirpath, rows, runs)



# ---------------------------------------------------------------------------------------------------------
# k8scluster profile: the k8s_cluster-only collector against kube-state-metrics (collector-only/scripts/run-ksm-compare.sh)
# ---------------------------------------------------------------------------------------------------------

def by_label(dirpath, slug, metric, prefix):
    """{label value: [(t, v)]} for a metric whose series are split by one label (resource=..., kind=...)."""
    return {k.split("=", 1)[-1]: v for k, v in load(dirpath, slug, metric).items() if k.startswith(prefix)}


def ksm_rows(dirpath, runs):
    rows = []
    for r in runs:
        if r["kind"] == "timeline":
            continue
        s = r["slug"]
        rows.append({
            "run": r,
            "ccpu": stats(total(dirpath, s, "collector_cpu_cores")), "cwss": tuple(x * MiB for x in stats(total(dirpath, s, "collector_wss_bytes"))),
            "crss": tuple(x * MiB for x in stats(total(dirpath, s, "collector_rss_bytes"))), "cpoints": stats(total(dirpath, s, "receiver_accepted_points_s")),
            "crefused": stats(total(dirpath, s, "receiver_refused_points_s"))[2],
            "kcpu": stats(total(dirpath, s, "ksm_cpu_cores")), "kwss": tuple(x * MiB for x in stats(total(dirpath, s, "ksm_wss_bytes"))),
            "krss": tuple(x * MiB for x in stats(total(dirpath, s, "ksm_rss_bytes"))), "ksamples": stats(total(dirpath, s, "ksm_samples_per_scrape")),
            "list_s": stats(total(dirpath, s, "apiserver_list_s")), "watch_s": stats(total(dirpath, s, "apiserver_watch_s")),
            "watchers": stats(total(dirpath, s, "apiserver_watchers")), "api_cpu": stats(total(dirpath, s, "apiserver_cpu_cores")),
            "kcm_cpu": stats(total(dirpath, s, "kcm_cpu_cores")), "etcd_cpu": stats(total(dirpath, s, "etcd_cpu_cores")),
            "objects": {k: stats(v)[2] for k, v in by_label(dirpath, s, "apiserver_storage_objects", "resource=").items()},
        })
    return rows


def ksm_audit(dirpath):
    """{(phase, user): {verb: count}} from raw/audit-requests.csv, if present."""
    f = os.path.join(dirpath, "raw", "audit-requests.csv"); out = defaultdict(lambda: defaultdict(int))
    if os.path.exists(f):
        for row in csv.DictReader(open(f)):
            out[(row["phase"], row["user"])][row["verb"]] += int(row["requests"])
    return out


def ksm_chart_timeline(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "timeline"]:
        s = r["slug"]
        objs = by_label(dirpath, s, "apiserver_storage_objects", "resource=")
        lists = total(dirpath, s, "apiserver_list_s"); watches = total(dirpath, s, "apiserver_watch_s"); watchers = total(dirpath, s, "apiserver_watchers")
        panels = [
            ("thousand objects", [(k, v, 0.001) for k, v in sorted(objs.items()) if k.split(".")[0] in ("deployments", "replicasets", "configmaps", "services", "pods", "horizontalpodautoscalers")]),
            ("CPU cores", [("k8s_cluster collector", total(dirpath, s, "collector_cpu_cores"), 1), ("kube-state-metrics", total(dirpath, s, "ksm_cpu_cores"), 1)]),
            ("working set MiB", [("k8s_cluster collector", total(dirpath, s, "collector_wss_bytes"), MiB), ("kube-state-metrics", total(dirpath, s, "ksm_wss_bytes"), MiB)]),
            ("RSS MiB", [("k8s_cluster collector", total(dirpath, s, "collector_rss_bytes"), MiB), ("kube-state-metrics", total(dirpath, s, "ksm_rss_bytes"), MiB)]),
            ("collector data points/s", [("accepted", total(dirpath, s, "receiver_accepted_points_s"), 1), ("refused", total(dirpath, s, "receiver_refused_points_s"), 1)]),
            ("kube-state-metrics samples per scrape (thousands)", [("samples", total(dirpath, s, "ksm_samples_per_scrape"), 0.001)]),
            ("API server requests/s, all clients", [("LIST", lists, 1), ("WATCH starts", watches, 1)]),
            ("open watches, all clients", [("watches", watchers, 1)]),
            ("control plane CPU cores", [("kube-apiserver (3)", total(dirpath, s, "apiserver_cpu_cores"), 1), ("kube-controller-manager", total(dirpath, s, "kcm_cpu_cores"), 1), ("etcd (3)", total(dirpath, s, "etcd_cpu_cores"), 1)]),
        ]
        fig, axes = plt.subplots(len(panels), 1, figsize=(9, 2.1 * len(panels)), sharex=True)
        markers = [(datetime.fromtimestamp(m["ts"], timezone.utc), m["name"]) for m in r.get("markers", [])]
        for ax, (ylabel, items) in zip(axes, panels):
            for i, (lab, pts, scale) in enumerate(items):
                if pts:
                    ax.plot([t for t, _ in pts], [v * scale for _, v in pts], color=SERIES[i % len(SERIES)], label=lab.split(".")[0])
            ax.set_ylabel(ylabel, fontsize=8); ax.set_ylim(bottom=0)
            if len(items) > 1:
                ax.legend(loc="upper left", fontsize=7, ncol=2)
            for t, _ in markers:
                ax.axvline(t, color=MUTED, linewidth=1, linestyle="--")
        for t, text in markers:
            axes[0].annotate(text, (t, axes[0].get_ylim()[1]), textcoords="offset points", xytext=(2, -9), fontsize=7, color=MUTED, rotation=90, va="top")
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc)); axes[-1].set_xlabel("time (UTC)")
        fig.suptitle("k8s_cluster receiver against kube-state-metrics: inventory creation, steady state, collector restart, churn", color=TEXT)
        fig.tight_layout(); fig.savefig(os.path.join(outdir, "ksm_timeline.png")); plt.close(fig)


def ksm_chart_phases(dirpath, rows, outdir):
    if not rows:
        return
    names = [r["run"]["label"].split(":")[0] for r in rows]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    import numpy as np
    x = np.arange(len(rows)); w = 0.38
    for ax, (ckey, kkey, idx, ylabel, fmt) in zip(axes, (("ccpu", "kcpu", 0, "CPU cores, average", "{:.3f}"), ("cwss", "kwss", 0, "working set MiB, average", "{:.0f}"), ("crss", "krss", 2, "RSS MiB, max", "{:.0f}"))):
        cv = [r[ckey][idx] for r in rows]; kv = [r[kkey][idx] for r in rows]
        b1 = ax.bar(x - w / 2, cv, w, color=SERIES[0], label="k8s_cluster collector"); b2 = ax.bar(x + w / 2, kv, w, color=SERIES[1], label="kube-state-metrics")
        for b, v in list(zip(b1, cv)) + list(zip(b2, kv)):
            label_point(ax, b.get_x() + b.get_width() / 2, v, fmt.format(v))
        ax.set_xticks(x); ax.set_xticklabels(names, rotation=20, fontsize=8); ax.set_ylabel(ylabel); ax.set_ylim(0, max(cv + kv) * 1.2 if cv + kv else 1); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Per phase: the k8s_cluster-only collector against kube-state-metrics on the same cluster", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "ksm_phases.png")); plt.close(fig)


def ksm_summary(dirpath, rows, runs):
    audit = ksm_audit(dirpath)
    env = {}
    f = os.path.join(dirpath, "raw", "phases.env")
    if os.path.exists(f):
        for line in open(f):
            if "=" in line:
                k, v = line.strip().split("=", 1); env[k] = v.strip('"')
    cl = runs[0]["cluster"] if runs else {}
    head = [f"Cluster: OpenShift {cl.get('version')} on {cl.get('platform')}, {cl.get('nodes')} nodes. Collector image: {runs[0].get('collector_image', '')}.", ""]
    if env:
        seen_c = env.get('CREATE_SEEN_COLLECTOR')
        seen_c = f"{seen_c} s" if seen_c not in (None, "none") else f"before the apply ended ({env.get('CREATE_SEEN_COLLECTOR_NOTE', 'not measured')})"
        head += [f"Inventory applied in {int(env.get('CREATE_END', 0)) - int(env.get('CREATE_START', 0))} s; full inventory seen by the collector {seen_c} and by kube-state-metrics {env.get('CREATE_SEEN_KSM')} s after the apply ended (30 s scrape and collection intervals, 10 s polling); after a collector restart the full inventory was back after {env.get('RESTART_SEEN_COLLECTOR')} s.", ""]
    lines = ["| phase | pods | deployments / replicasets / configmaps / services stored | collector CPU avg / p95 | collector WSS MiB avg / max | collector RSS MiB max | collector points/s | kube-state-metrics CPU avg / p95 | kube-state-metrics WSS MiB avg / max | kube-state-metrics RSS MiB max | kube-state-metrics samples per scrape | API server LIST/s | WATCH starts/s | open watches | kube-apiserver CPU | kube-controller-manager CPU | audit: collector list / watch | audit: kube-state-metrics list / watch |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        run = r["run"]; name = run["label"].split(":")[0]; o = r["objects"]
        ac = audit.get((name, "otel-k8scluster"), {}); ak = audit.get((name, "kube-state-metrics"), {})
        lines.append(f"| {name} | {run['cluster']['pods_running']} | {o.get('deployments.apps', 0):,.0f} / {o.get('replicasets.apps', 0):,.0f} / {o.get('configmaps', 0):,.0f} / {o.get('services', 0):,.0f} | {r['ccpu'][0]:.3f} / {r['ccpu'][1]:.3f} | {r['cwss'][0]:.0f} / {r['cwss'][2]:.0f} | {r['crss'][2]:.0f} | {r['cpoints'][0]:,.0f} | {r['kcpu'][0]:.3f} / {r['kcpu'][1]:.3f} | {r['kwss'][0]:.0f} / {r['kwss'][2]:.0f} | {r['krss'][2]:.0f} | {r['ksamples'][0]:,.0f} | {r['list_s'][0]:.2f} | {r['watch_s'][0]:.2f} | {r['watchers'][0]:.0f} | {r['api_cpu'][0]:.2f} | {r['kcm_cpu'][0]:.2f} | {ac.get('list', 0)} / {ac.get('watch', 0)} | {ak.get('list', 0)} / {ak.get('watch', 0)} |")
    with open(os.path.join(dirpath, "summary.md"), "w") as f:
        f.write("\n".join(head + lines) + "\n")


def render_k8scluster(dirpath, runs, outdir):
    rows = ksm_rows(dirpath, runs)
    ksm_chart_timeline(dirpath, runs, outdir)
    ksm_chart_phases(dirpath, rows, outdir)
    ksm_summary(dirpath, rows, runs)

# k8scluster-scale profile: the scale ladder of the k8s_cluster-only collector against kube-state-metrics
# (collector-only/scripts/run-scale-ladder.sh; runs labelled "<N>k <phase>: ...", one step per inventory size)
# ---------------------------------------------------------------------------------------------------------

# the kinds each client watches, as apiserver_storage_objects resource names (the receiver has no informer for
# config maps, secrets or endpoints; kube-state-metrics watches them and more)
RECEIVER_KINDS = {"deployments.apps", "replicasets.apps", "services", "jobs.batch", "cronjobs.batch", "horizontalpodautoscalers.autoscaling", "resourcequotas", "clusterresourcequotas.quota.openshift.io", "namespaces", "pods"}
KSM_KINDS = RECEIVER_KINDS | {"configmaps", "secrets", "endpoints"}


def scale_steps(dirpath, runs):
    """One row per ladder step with the steady, restart, restart-ksm, churn and create runs of that step."""
    steps = {}
    for r in runs:
        if r["kind"] == "timeline" or " " not in r["label"]:
            continue
        step, rest = r["label"].split(" ", 1); phase = rest.split(":")[0]
        steps.setdefault(step, {"step": step, "units": r.get("units", 0), "runs": {}})["runs"][phase] = r
    env = {}
    f = os.path.join(dirpath, "raw", "phases.env")
    if os.path.exists(f):
        for line in open(f):
            if "=" in line:
                k, v = line.strip().split("=", 1); env[k] = v.strip('"')
    lists = defaultdict(list)
    f = os.path.join(dirpath, "raw", "audit-lists.csv")
    if os.path.exists(f):
        for row in csv.DictReader(open(f)):
            lists[(row["tag"], row["user"])].append(row)
    audit = defaultdict(lambda: defaultdict(int))
    f = os.path.join(dirpath, "raw", "audit-requests.csv")
    if os.path.exists(f):
        for row in csv.DictReader(open(f)):
            audit[(row["tag"], row["user"])][row["verb"]] += int(row["requests"])
    rows = []
    # points the receiver emits per object and collection cycle for the kinds of the load (deployment: desired, available;
    # replica set: desired, available; job: 5; cron job: 1; HPA: 4; resource quota: hard and used of one resource; namespace: phase)
    PER_OBJECT = {"deployments.apps": 2, "replicasets.apps": 2, "jobs.batch": 5, "cronjobs.batch": 1, "horizontalpodautoscalers.autoscaling": 4, "resourcequotas": 2, "namespaces": 1}
    base = None
    for step in sorted(steps.values(), key=lambda x: x["units"]):
        st = step["runs"].get("steady") or step["runs"].get("create"); rs = step["runs"].get("restart"); rk = step["runs"].get("restart-ksm"); ch = step["runs"].get("churn")
        if not st:
            continue
        s = st["slug"]; objs = {k: stats(v)[2] for k, v in by_label(dirpath, s, "apiserver_storage_objects", "resource=").items()}
        t = step["step"]
        def mx(run, metric):
            return stats(total(dirpath, run["slug"], metric))[2] if run else 0.0
        def dur(l): return float(l["duration_s"]) if l.get("duration_s") not in (None, "") else 0.0
        def longest(tag, user, run):
            """The slowest start-up request: a LIST by its audit duration, or an initial-events watch by the watch-list histogram."""
            ls = lists.get((tag, user), [])
            if not ls: return None
            wl = {k: max((x for _, x in v), default=0.0) for k, v in by_label(dirpath, run["slug"], "apiserver_watchlist_duration_s", "resource=").items()} if run else {}
            for l in ls:
                l["duration_s"] = l["duration_s"] if l.get("duration_s") not in (None, "") else wl.get(l["resource"], 0.0)
            return max(ls, key=dur)
        def list_bytes(run, resource):
            if not run: return 0.0
            v = by_label(dirpath, run["slug"], "apiserver_list_bytes", "resource=").get(resource, [])
            return max((x for _, x in v), default=0.0)
        lc, lk = longest(f"{t}-restart", "otel-k8scluster", rs), longest(f"{t}-restart-ksm", "kube-state-metrics", rk)
        cpoints = stats(total(dirpath, s, "receiver_accepted_points_s"))
        if base is None:
            base = (cpoints[0] * 30, objs)  # the empty-inventory step: measured points per cycle and its objects
        expected = base[0] + sum((objs.get(k, 0) - base[1].get(k, 0)) * n for k, n in PER_OBJECT.items())
        rows.append({
            "expected_cycle": expected, "measured_cycle": cpoints[0] * 30,
            "step": t, "units": step["units"], "runs": step["runs"], "objects": objs,
            "stored": stats(total(dirpath, s, "apiserver_storage_objects_total"))[2],
            "watched_receiver": sum(v for k, v in objs.items() if k in RECEIVER_KINDS), "watched_ksm": sum(v for k, v in objs.items() if k in KSM_KINDS),
            "ccpu": stats(total(dirpath, s, "collector_cpu_cores")), "cwss": tuple(x * MiB for x in stats(total(dirpath, s, "collector_wss_bytes"))),
            "crss": tuple(x * MiB for x in stats(total(dirpath, s, "collector_rss_bytes"))), "cpoints": stats(total(dirpath, s, "receiver_accepted_points_s")),
            "crefused": stats(total(dirpath, s, "receiver_refused_points_s"))[2] + stats(total(dirpath, s, "memory_limiter_refused_points_s"))[2],
            "cwss_max_step": max(mx(r, "collector_wss_bytes") for r in step["runs"].values()) * MiB, "crss_max_step": max(mx(r, "collector_rss_bytes") for r in step["runs"].values()) * MiB,
            "crestarts": max(mx(r, "collector_restarts_total") for r in step["runs"].values()), "coom": max(mx(r, "collector_oom_killed") for r in step["runs"].values()),
            "ccpu_churn": stats(total(dirpath, ch["slug"], "collector_cpu_cores"))[1] if ch else 0.0, "kcpu_churn": stats(total(dirpath, ch["slug"], "ksm_cpu_cores"))[1] if ch else 0.0,
            "kcpu": stats(total(dirpath, s, "ksm_cpu_cores")), "kwss": tuple(x * MiB for x in stats(total(dirpath, s, "ksm_wss_bytes"))),
            "krss": tuple(x * MiB for x in stats(total(dirpath, s, "ksm_rss_bytes"))), "ksamples": stats(total(dirpath, s, "ksm_samples_per_scrape")),
            "kscrape": stats(total(dirpath, s, "ksm_scrape_duration_s")), "kup": stats(total(dirpath, s, "ksm_up"))[0],
            "kwss_max_step": max(mx(r, "ksm_wss_bytes") for r in step["runs"].values()) * MiB, "krss_max_step": max(mx(r, "ksm_rss_bytes") for r in step["runs"].values()) * MiB,
            "seen_create_c": env.get(f"CREATE_SEEN_COLLECTOR_{t}", "-"), "seen_create_k": env.get(f"CREATE_SEEN_KSM_{t}", "-"),
            "seen_restart_c": env.get(f"RESTART_SEEN_COLLECTOR_{t}", "-"), "seen_restart_k": env.get(f"RESTART_SEEN_KSM_{t}", "-"),
            "create_s": int(env.get(f"CREATE_END_{t}", 0)) - int(env.get(f"CREATE_START_{t}", 0)),
            "audit_c": audit.get((f"{t}-restart", "otel-k8scluster"), {}), "audit_k": audit.get((f"{t}-restart-ksm", "kube-state-metrics"), {}),
            "audit_steady_c": audit.get((f"{t}-steady", "otel-k8scluster"), {}), "audit_steady_k": audit.get((f"{t}-steady", "kube-state-metrics"), {}),
            "lists_c": lists.get((f"{t}-restart", "otel-k8scluster"), []), "lists_k": lists.get((f"{t}-restart-ksm", "kube-state-metrics"), []),
            "longest_c": lc, "longest_k": lk, "longest_c_bytes": list_bytes(rs, lc["resource"]) if lc else 0.0, "longest_k_bytes": list_bytes(rk, lk["resource"]) if lk else 0.0,
            "kind_c": (lc or {}).get("verb", "-"), "kind_k": (lk or {}).get("verb", "-"),
            "api_cpu": stats(total(dirpath, s, "apiserver_cpu_cores")), "api_wss_max": stats(total(dirpath, s, "apiserver_wss_bytes_max_pod"))[2] * MiB,
            "etcd_cpu": stats(total(dirpath, s, "etcd_cpu_cores")), "etcd_db": stats(total(dirpath, s, "etcd_db_bytes"))[2] * MiB, "etcd_fsync": stats(total(dirpath, s, "etcd_fsync_p99_s"))[1],
            "kcm_cpu": stats(total(dirpath, s, "kcm_cpu_cores")), "list_s": stats(total(dirpath, s, "apiserver_list_s")), "watch_s": stats(total(dirpath, s, "apiserver_watch_s")),
            "prom_wss": stats(total(dirpath, s, "prometheus_k8s_wss_bytes"))[2] * MiB, "vendor_wss": stats(total(dirpath, s, "vendor_prometheus_wss_bytes"))[2] * MiB,
            "restart_api_cpu": stats(total(dirpath, rs["slug"], "apiserver_cpu_cores"))[2] if rs else 0.0, "restart_ksm_api_cpu": stats(total(dirpath, rk["slug"], "apiserver_cpu_cores"))[2] if rk else 0.0,
        })
    return rows


def scale_fit(rows, xkey, ykey):
    """Least squares y = a + b x over the steps -> (a, b) or None."""
    pts = [(r[xkey], r[ykey] if not isinstance(r[ykey], tuple) else r[ykey][0]) for r in rows]
    if len(pts) < 2:
        return None
    n = len(pts); sx = sum(x for x, _ in pts); sy = sum(y for _, y in pts); sxx = sum(x * x for x, _ in pts); sxy = sum(x * y for x, y in pts)
    d = n * sxx - sx * sx
    if d == 0:
        return None
    b = (n * sxy - sx * sy) / d; return (sy - b * sx) / n, b


def scale_chart_memory(rows, outdir):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    xs = [r["stored"] / 1000 for r in rows]
    for ax, (ckey, kkey, title) in zip(axes, (("cwss", "kwss", "working set MiB, steady average"), ("cwss_max_step", "kwss_max_step", "working set MiB, max over the step (restarts and churn included)"), ("crss_max_step", "krss_max_step", "RSS MiB, max over the step"))):
        cv = [r[ckey][0] if isinstance(r[ckey], tuple) else r[ckey] for r in rows]; kv = [r[kkey][0] if isinstance(r[kkey], tuple) else r[kkey] for r in rows]
        ax.plot(xs, cv, marker="o", color=SERIES[0], label="k8s_cluster collector"); ax.plot(xs, kv, marker="s", color=SERIES[1], label="kube-state-metrics")
        for x, c, k, r in zip(xs, cv, kv, rows):
            label_point(ax, x, c, f"{c:.0f}"); label_point(ax, x, k, f"{k:.0f}", dy=-12)
        ax.set_xlabel("objects stored in etcd (thousands)"); ax.set_title(title, fontsize=9); ax.set_ylim(bottom=0); ax.legend(fontsize=8, loc="upper left")
    fc = scale_fit(rows, "watched_receiver", "cwss"); fk = scale_fit(rows, "watched_ksm", "kwss")
    sub = []
    if fc: sub.append(f"collector: {fc[0]:.0f} MiB + {fc[1] * 1000:.1f} MiB per 1,000 watched objects")
    if fk: sub.append(f"kube-state-metrics: {fk[0]:.0f} MiB + {fk[1] * 1000:.1f} MiB per 1,000 watched objects")
    fig.suptitle("Memory against the object inventory (per client, over the objects it watches: " + "; ".join(sub) + ")", color=TEXT, fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "scale_memory_vs_objects.png")); plt.close(fig)


def scale_chart_cpu(rows, outdir):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    xs = [r["stored"] / 1000 for r in rows]
    panels = (("ccpu", "kcpu", 0, "CPU cores, steady average"), ("ccpu_churn", "kcpu_churn", None, "CPU cores, p95 during the churn"), ("cpoints", "ksamples", 0, "data: collector points/s, kube-state-metrics samples per scrape (thousands)"))
    for ax, (ckey, kkey, idx, title) in zip(axes, panels):
        cv = [r[ckey][idx] if idx is not None else r[ckey] for r in rows]; kv = [r[kkey][idx] if idx is not None else r[kkey] for r in rows]
        if ckey == "cpoints":
            kv = [v / 1000 for v in kv]
        ax.plot(xs, cv, marker="o", color=SERIES[0], label="k8s_cluster collector" + (" points/s" if ckey == "cpoints" else "")); ax.plot(xs, kv, marker="s", color=SERIES[1], label="kube-state-metrics" + (" thousand samples/scrape" if ckey == "cpoints" else ""))
        for x, c, k in zip(xs, cv, kv):
            label_point(ax, x, c, f"{c:,.3f}" if ckey != "cpoints" else f"{c:,.0f}"); label_point(ax, x, k, f"{k:,.3f}" if ckey != "cpoints" else f"{k:,.0f}", dy=-12)
        ax.set_xlabel("objects stored in etcd (thousands)"); ax.set_title(title, fontsize=9); ax.set_ylim(bottom=0); ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("CPU and data volume against the object inventory", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "scale_cpu_vs_objects.png")); plt.close(fig)


def scale_chart_inventory(rows, outdir):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    xs = [r["stored"] / 1000 for r in rows]
    def num(v):
        try: return float(v)
        except (TypeError, ValueError): return float("nan")
    ax = axes[0]
    ax.plot(xs, [num(r["seen_restart_c"]) for r in rows], marker="o", color=SERIES[0], label="k8s_cluster collector (first full collection after the pod start)")
    ax.plot(xs, [num(r["seen_restart_k"]) for r in rows], marker="s", color=SERIES[1], label="kube-state-metrics (first full scrape after the pod start)")
    for x, r in zip(xs, rows):
        label_point(ax, x, num(r["seen_restart_c"]), f"{r['seen_restart_c']} s"); label_point(ax, x, num(r["seen_restart_k"]), f"{r['seen_restart_k']} s", dy=-12)
    ax.set_xlabel("objects stored in etcd (thousands)"); ax.set_ylabel("seconds"); ax.set_title("time to the full inventory after a restart (30 s intervals, 5 s polling)", fontsize=9); ax.set_ylim(bottom=0); ax.legend(fontsize=8, loc="upper left")
    ax = axes[1]
    def dur(l): return float(l["duration_s"]) if l.get("duration_s") not in (None, "") else 0.0
    ax.plot(xs, [sum(dur(l) for l in r["lists_c"]) for r in rows], marker="o", color=SERIES[0], label="k8s_cluster collector: sum of the start-up list durations")
    ax.plot(xs, [dur(r["longest_c"]) if r["longest_c"] else 0 for r in rows], marker="o", color=SERIES[0], linestyle="--", label="k8s_cluster collector: longest")
    ax.plot(xs, [sum(dur(l) for l in r["lists_k"]) for r in rows], marker="s", color=SERIES[1], label="kube-state-metrics: sum of the start-up list durations")
    ax.plot(xs, [dur(r["longest_k"]) if r["longest_k"] else 0 for r in rows], marker="s", color=SERIES[1], linestyle="--", label="kube-state-metrics: longest")
    for x, r in zip(xs, rows):
        if r["longest_c"]: label_point(ax, x, dur(r["longest_c"]), r["longest_c"]["resource"])
        if r["longest_k"]: label_point(ax, x, dur(r["longest_k"]), r["longest_k"]["resource"], dy=-12)
    ax.set_xlabel("objects stored in etcd (thousands)"); ax.set_ylabel("seconds"); ax.set_title("start-up lists: LIST requests (audit log) or watch-list streams (apiserver_watch_list_duration_seconds)", fontsize=8); ax.set_ylim(bottom=0); ax.legend(fontsize=7, loc="upper left")
    fig.suptitle("Start-up: time to the full inventory and the LIST requests behind it", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "scale_inventory_time.png")); plt.close(fig)


def scale_chart_control_plane(rows, outdir):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    xs = [r["stored"] / 1000 for r in rows]
    ax = axes[0]
    ax.plot(xs, [r["api_cpu"][0] for r in rows], marker="o", color=SERIES[0], label="kube-apiserver (3), steady")
    ax.plot(xs, [r["restart_api_cpu"] for r in rows], marker="o", color=SERIES[0], linestyle="--", label="kube-apiserver peak, collector restart")
    ax.plot(xs, [r["restart_ksm_api_cpu"] for r in rows], marker="s", color=SERIES[1], linestyle="--", label="kube-apiserver peak, kube-state-metrics restart")
    ax.plot(xs, [r["etcd_cpu"][0] for r in rows], marker="^", color=SERIES[2], label="etcd (3), steady"); ax.plot(xs, [r["kcm_cpu"][0] for r in rows], marker="v", color=SERIES[3], label="kube-controller-manager, steady")
    ax.set_title("control plane CPU cores", fontsize=9); ax.set_ylim(bottom=0); ax.legend(fontsize=7, loc="upper left")
    ax = axes[1]
    ax.plot(xs, [r["api_wss_max"] / 1024 for r in rows], marker="o", color=SERIES[0], label="kube-apiserver, busiest instance (GiB)"); ax.plot(xs, [r["etcd_db"] for r in rows], marker="^", color=SERIES[2], label="etcd database size (MiB)")
    for x, r in zip(xs, rows):
        label_point(ax, x, r["api_wss_max"] / 1024, f"{r['api_wss_max'] / 1024:.1f} GiB"); label_point(ax, x, r["etcd_db"], f"{r['etcd_db']:.0f} MiB", dy=-12)
    ax.set_title("API server working set and etcd database", fontsize=9); ax.set_ylim(bottom=0); ax.legend(fontsize=7, loc="upper left")
    ax = axes[2]
    ax.plot(xs, [r["list_s"][0] for r in rows], marker="o", color=SERIES[0], label="LIST/s, all clients, steady"); ax.plot(xs, [r["watch_s"][0] for r in rows], marker="s", color=SERIES[1], label="WATCH starts/s, all clients, steady")
    ax.plot(xs, [r["kscrape"][2] for r in rows], marker="^", color=SERIES[2], label="kube-state-metrics scrape duration, max (s)")
    ax.set_title("API server requests and the kube-state-metrics scrape", fontsize=9); ax.set_ylim(bottom=0); ax.legend(fontsize=7, loc="upper left")
    for ax in axes:
        ax.set_xlabel("objects stored in etcd (thousands)")
    fig.suptitle("Control plane cost of the inventory", color=TEXT)
    fig.tight_layout(); fig.savefig(os.path.join(outdir, "scale_control_plane.png")); plt.close(fig)


def scale_chart_timeline(dirpath, runs, outdir):
    for r in [r for r in runs if r["kind"] == "timeline"]:
        s = r["slug"]
        objs = by_label(dirpath, s, "apiserver_storage_objects", "resource=")
        panels = [
            ("thousand objects stored", [("all", total(dirpath, s, "apiserver_storage_objects_total"), 0.001)] + [(k, v, 0.001) for k, v in sorted(objs.items()) if k.split(".")[0] in ("configmaps", "secrets", "deployments", "replicasets", "services", "jobs")]),
            ("CPU cores", [("k8s_cluster collector", total(dirpath, s, "collector_cpu_cores"), 1), ("kube-state-metrics", total(dirpath, s, "ksm_cpu_cores"), 1)]),
            ("working set MiB", [("k8s_cluster collector", total(dirpath, s, "collector_wss_bytes"), MiB), ("kube-state-metrics", total(dirpath, s, "ksm_wss_bytes"), MiB)]),
            ("RSS MiB", [("k8s_cluster collector", total(dirpath, s, "collector_rss_bytes"), MiB), ("kube-state-metrics", total(dirpath, s, "ksm_rss_bytes"), MiB)]),
            ("collector data points/s", [("accepted", total(dirpath, s, "receiver_accepted_points_s"), 1), ("refused", total(dirpath, s, "receiver_refused_points_s"), 1), ("memory_limiter refused", total(dirpath, s, "memory_limiter_refused_points_s"), 1)]),
            ("kube-state-metrics: thousand samples per scrape, scrape seconds", [("samples (thousands)", total(dirpath, s, "ksm_samples_per_scrape"), 0.001), ("scrape duration s", total(dirpath, s, "ksm_scrape_duration_s"), 1)]),
            ("API server requests/s, all clients", [("LIST", total(dirpath, s, "apiserver_list_s"), 1), ("WATCH starts", total(dirpath, s, "apiserver_watch_s"), 1), ("429", total(dirpath, s, "apiserver_429_s"), 1)]),
            ("control plane CPU cores", [("kube-apiserver (3)", total(dirpath, s, "apiserver_cpu_cores"), 1), ("kube-controller-manager", total(dirpath, s, "kcm_cpu_cores"), 1), ("etcd (3)", total(dirpath, s, "etcd_cpu_cores"), 1)]),
            ("control plane memory GiB, etcd database MiB", [("kube-apiserver busiest instance (GiB)", total(dirpath, s, "apiserver_wss_bytes_max_pod"), MiB / 1024), ("etcd database (MiB)", total(dirpath, s, "etcd_db_bytes"), MiB), ("kube-controller-manager (GiB)", total(dirpath, s, "kcm_wss_bytes"), MiB / 1024)]),
            ("monitoring memory GiB", [("prometheus-k8s busiest", total(dirpath, s, "prometheus_k8s_wss_bytes"), MiB / 1024), ("vendor Prometheus", total(dirpath, s, "vendor_prometheus_wss_bytes"), MiB / 1024)]),
        ]
        fig, axes = plt.subplots(len(panels), 1, figsize=(10, 2.1 * len(panels)), sharex=True)
        markers = [(datetime.fromtimestamp(m["ts"], timezone.utc), m["name"]) for m in r.get("markers", [])]
        for ax, (ylabel, items) in zip(axes, panels):
            for i, (lab, pts, scale) in enumerate(items):
                if pts:
                    ax.plot([t for t, _ in pts], [v * scale for _, v in pts], color=SERIES[i % len(SERIES)], label=lab.split(".")[0], linewidth=1.5)
            ax.set_ylabel(ylabel, fontsize=7); ax.set_ylim(bottom=0)
            if len(items) > 1:
                ax.legend(loc="upper left", fontsize=6, ncol=3)
            for t, _ in markers:
                ax.axvline(t, color=MUTED, linewidth=0.8, linestyle="--")
        for t, text in markers:
            axes[0].annotate(text, (t, axes[0].get_ylim()[1]), textcoords="offset points", xytext=(2, -9), fontsize=6, color=MUTED, rotation=90, va="top")
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=timezone.utc)); axes[-1].set_xlabel("time (UTC)")
        fig.suptitle("Scale ladder: the k8s_cluster receiver against kube-state-metrics while the inventory grows", color=TEXT)
        fig.tight_layout(); fig.savefig(os.path.join(outdir, "scale_timeline.png")); plt.close(fig)


def scale_summary(dirpath, rows, runs):
    cl = runs[0]["cluster"] if runs else {}
    head = [f"Cluster: OpenShift {cl.get('version')} on {cl.get('platform')}, {cl.get('nodes')} nodes. Collector image: {runs[0].get('collector_image', '')}.", "",
            "Objects: stored = sum over the resources of apiserver_storage_objects; watched = the stored objects of the kinds the client has an informer for (the collector: pods, namespaces, deployments, replica sets, services, jobs, cron jobs, HPAs, quotas, cluster resource quotas; kube-state-metrics: those plus config maps, secrets and endpoints). Steady values are averages over the 20 min steady window, max values the maximum over all phases of the step. Inventory times: seconds after the loader ended (create) or after the pod start (restart) until the client reported every deployment of the inventory, 30 s intervals and 5 to 10 s polling. LIST rows come from the audit log of the restart windows. Points per cycle: the receiver's accepted points per 30 s cycle (rate x 30) against the points the inventory should produce (the empty-inventory rate plus 2 per deployment and replica set, 5 per job, 1 per cron job, 4 per HPA, 2 per quota, 1 per namespace): 100 % means the receiver keeps its interval.", ""]
    lines = ["| step | objects stored / watched by collector / by kube-state-metrics | loader s | collector CPU avg / churn p95 | collector WSS MiB avg / max | collector RSS MiB max | collector points/s | points per cycle measured / expected | refused pts/s | collector restarts (OOM) | kube-state-metrics CPU avg / churn p95 | kube-state-metrics WSS MiB avg / max | kube-state-metrics RSS MiB max | samples per scrape / scrape s max | inventory after create: collector / ksm | inventory after restart: collector / ksm | collector LISTs (count, sum s, longest) | kube-state-metrics LISTs (count, sum s, longest) | kube-apiserver CPU steady / peak at restarts | kube-apiserver WSS GiB max | etcd db MiB / fsync p99 s | LIST/s all clients |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lc, lk = r["longest_c"], r["longest_k"]
        def dur(l): return float(l["duration_s"]) if l.get("duration_s") not in (None, "") else 0.0
        lcs = f"{len(r['lists_c'])} ({r['kind_c']}), {sum(dur(l) for l in r['lists_c']):.1f} s, {lc['resource']} {dur(lc):.2f} s" if lc else "-"
        lks = f"{len(r['lists_k'])} ({r['kind_k']}), {sum(dur(l) for l in r['lists_k']):.1f} s, {lk['resource']} {dur(lk):.2f} s" if lk else "-"
        lines.append(f"| {r['step']} | {r['stored']:,.0f} / {r['watched_receiver']:,.0f} / {r['watched_ksm']:,.0f} | {r['create_s']} | {r['ccpu'][0]:.3f} / {r['ccpu_churn']:.3f} | {r['cwss'][0]:.0f} / {r['cwss_max_step']:.0f} | {r['crss_max_step']:.0f} | {r['cpoints'][0]:,.0f} | {r['measured_cycle']:,.0f} / {r['expected_cycle']:,.0f} ({100 * r['measured_cycle'] / r['expected_cycle']:.0f} %) | {r['crefused']:.0f} | {r['crestarts']:.0f} ({'yes' if r['coom'] else 'no'}) | {r['kcpu'][0]:.3f} / {r['kcpu_churn']:.3f} | {r['kwss'][0]:.0f} / {r['kwss_max_step']:.0f} | {r['krss_max_step']:.0f} | {r['ksamples'][0]:,.0f} / {r['kscrape'][2]:.1f} | {r['seen_create_c']} / {r['seen_create_k']} | {r['seen_restart_c']} / {r['seen_restart_k']} | {lcs} | {lks} | {r['api_cpu'][0]:.2f} / {max(r['restart_api_cpu'], r['restart_ksm_api_cpu']):.2f} | {r['api_wss_max'] / 1024:.1f} | {r['etcd_db']:,.0f} / {r['etcd_fsync']:.3f} | {r['list_s'][0]:.1f} |")
    fc = scale_fit(rows, "watched_receiver", "cwss"); fk = scale_fit(rows, "watched_ksm", "kwss")
    fcr = scale_fit(rows, "watched_receiver", "crss_max_step"); fkr = scale_fit(rows, "watched_ksm", "krss_max_step")
    fits = ["", "Linear fits over the steps (per watched object of each client):"]
    if fc: fits.append(f"- collector working set, steady: {fc[0]:.0f} MiB + {fc[1] * 100000:.0f} MiB per 100,000 watched objects")
    if fcr: fits.append(f"- collector RSS, max over the step: {fcr[0]:.0f} MiB + {fcr[1] * 100000:.0f} MiB per 100,000 watched objects")
    if fk: fits.append(f"- kube-state-metrics working set, steady: {fk[0]:.0f} MiB + {fk[1] * 100000:.0f} MiB per 100,000 watched objects")
    if fkr: fits.append(f"- kube-state-metrics RSS, max over the step: {fkr[0]:.0f} MiB + {fkr[1] * 100000:.0f} MiB per 100,000 watched objects")
    lists = ["", "Start-up requests per resource in the restart windows (audit log; a LIST has its duration from the audit event, an initial-events watch (client-go watch list) its streaming duration from apiserver_watch_list_duration_seconds and no response size):", "",
             "| step | client | resource | requests | kind | longest s | mean bytes per LIST of any client in the window (apiserver_response_sizes; a watch-list stream has no size metric) |", "|---|---|---|---|---|---|---|"]
    def dur(l): return float(l["duration_s"]) if l.get("duration_s") not in (None, "") else 0.0
    for r in rows:
        for user, key, run in (("collector", "lists_c", r["runs"].get("restart")), ("kube-state-metrics", "lists_k", r["runs"].get("restart-ksm"))):
            per = defaultdict(list); kinds = {}
            for l in r[key]:
                per[l["resource"]].append(dur(l)); kinds[l["resource"]] = l["verb"]
            sizes = {k: max((x for _, x in v), default=0.0) for k, v in by_label(dirpath, run["slug"], "apiserver_list_bytes", "resource=").items()} if run else {}
            for res, ds in sorted(per.items(), key=lambda kv: -max(kv[1]))[:8]:
                lists.append(f"| {r['step']} | {user} | {res} | {len(ds)} | {kinds[res]} | {max(ds):.2f} | {sizes.get(res, 0):,.0f} |")
    with open(os.path.join(dirpath, "summary.md"), "w") as f:
        f.write("\n".join(head + lines + fits + lists) + "\n")


def render_k8scluster_scale(dirpath, runs, outdir):
    rows = scale_steps(dirpath, runs)
    scale_chart_memory(rows, outdir); scale_chart_cpu(rows, outdir); scale_chart_inventory(rows, outdir); scale_chart_control_plane(rows, outdir)
    scale_chart_timeline(dirpath, runs, outdir); scale_summary(dirpath, rows, runs)


def main():
    dirpath = sys.argv[1]
    runs = json.load(open(os.path.join(dirpath, "runs.json")))
    outdir = os.path.join(dirpath, "charts"); os.makedirs(outdir, exist_ok=True)
    if runs and runs[0].get("profile") == "collector-only":
        render_collector_only(dirpath, runs, outdir)
        print("charts:", sorted(os.listdir(outdir)))
        return
    if runs and runs[0].get("profile") == "k8scluster":
        render_k8scluster(dirpath, runs, outdir)
        print("charts:", sorted(os.listdir(outdir)))
        return
    if runs and runs[0].get("profile") == "k8scluster-scale":
        render_k8scluster_scale(dirpath, runs, outdir)
        print("charts:", sorted(os.listdir(outdir)))
        return
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
