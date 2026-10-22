#!/usr/bin/env python3
"""Compare what the collectors emitted (file exporter dumps, OTLP JSON lines) with what the
senders had in their TSDB (raw samples from instant queries with a range selector) over the
windows of the run, and reconcile the sender and collector counters.

usage: scripts/compare.py <results dir>     (reads <dir>/raw, writes <dir>/compare-w1.md, compare-w2.md, compare.json)

Series identity: a Prometheus series is (name, labels without __name__). A dump data point maps
back to it with service.name -> job (service.namespace/service.name -> job when both exist),
service.instance.id -> instance, the data point attributes as the other labels. The external
labels of the platform Prometheus (prometheus, prometheus_replica) are not part of its own TSDB
series, so they are removed from the production dump keys and kept as the replica tag.
Range selectors are left-open: a window (S, E] keeps the samples with S*1000 < ts_ms <= E*1000.
"""
import json, math, os, re, sys
from collections import defaultdict, Counter

D = sys.argv[1]
RAW = os.path.join(D, "raw")
EXTERNAL = {"prometheus", "prometheus_replica"}
RESOURCE_SKIP = {"service.name", "service.instance.id", "service.namespace"}

def fnum(s):
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s)
    if s in ("NaN", "nan"): return float("nan")
    if s in ("+Inf", "Inf", "Infinity"): return float("inf")
    if s in ("-Inf", "-Infinity"): return float("-inf")
    return float(s)

def same(a, b):
    if math.isnan(a) and math.isnan(b): return True
    return a == b

def key_of(name, labels):
    return (name, tuple(sorted(labels.items())))

def load_json(name):
    p = os.path.join(RAW, name)
    if not os.path.exists(p): return None
    with open(p) as f:
        return json.load(f)

def load_fam(name):
    d = load_json(name)
    if not isinstance(d, dict) or "status" in d: return {}
    return {n: v for n, v in d.items() if isinstance(v, dict) and "error" not in v}

def windows():
    with open(os.path.join(RAW, "windows.txt")) as f:
        parts = f.read().split()
    return {1: (int(parts[1]), int(parts[2])), 2: (int(parts[3]), int(parts[4]))}

# ---------------------------------------------------------------- source (Prometheus TSDB)
def load_source(name, lo, hi):
    """returns floats: key -> {ts_ms: value}, hists: key -> {ts_ms: api histogram}"""
    d = load_json(name)
    floats, hists = {}, {}
    if not d or d.get("status") != "success":
        return floats, hists
    for r in d["data"]["result"]:
        m = dict(r["metric"]); nm = m.pop("__name__", "")
        k = key_of(nm, m)
        if "values" in r:
            pts = {}
            for ts, v in r["values"]:
                t = int(round(float(ts) * 1000))
                if lo * 1000 < t <= hi * 1000:
                    pts[t] = fnum(v)
            if pts: floats[k] = pts
        if "histograms" in r:
            pts = {}
            for ts, h in r["histograms"]:
                t = int(round(float(ts) * 1000))
                if lo * 1000 < t <= hi * 1000:
                    pts[t] = h
            if pts: hists[k] = pts
    return floats, hists

# ---------------------------------------------------------------- dump (file exporter JSON lines)
def attr_value(v):
    if "stringValue" in v: return v["stringValue"]
    if "intValue" in v: return str(v["intValue"])
    if "doubleValue" in v: return str(v["doubleValue"])
    if "boolValue" in v: return str(v["boolValue"]).lower()
    return json.dumps(v, sort_keys=True)

def attrs(lst):
    return {a["key"]: attr_value(a["value"]) for a in (lst or [])}

def dp_value(dp):
    if "asDouble" in dp: return fnum(dp["asDouble"])
    if "asInt" in dp: return float(int(dp["asInt"]))
    return float("nan")

class Dump:
    def __init__(self, path, lo, hi, strip_external):
        self.floats = defaultdict(lambda: defaultdict(list))   # key -> ts -> [values]  (list: duplicates); typed path (no replicas)
        self.hists = defaultdict(dict)                          # key -> ts -> dp
        self.by_rep = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # replica -> key -> ts -> [values]; production path
        self.flags = Counter()                                  # key -> count of NoRecordedValue points
        self.meta = {}                                          # name -> dict(kind, unit, description, monotonic, ptype, start_ts_seen)
        self.resources = defaultdict(set)                       # (job, instance) -> set of frozenset(extra resource attrs)
        self.replica = defaultdict(Counter)                     # key -> replica -> points
        self.exemplars = defaultdict(list)                      # key -> [exemplar dicts]
        self.points = 0; self.points_in_window = 0; self.lines = 0; self.bad_lines = 0
        self.names = Counter(); self.scopes = Counter(); self.empty_resource_points = 0
        self.first_ts = None; self.last_ts = None
        lo_ms, hi_ms = lo * 1000, hi * 1000
        with open(path) as f:
            for line in f:
                self.lines += 1
                try:
                    d = json.loads(line)
                except Exception:
                    self.bad_lines += 1; continue
                for rm in d.get("resourceMetrics", []):
                    ra = attrs(rm.get("resource", {}).get("attributes"))
                    job = ra.get("service.name", "")
                    if "service.namespace" in ra:
                        job = ra["service.namespace"] + "/" + job
                    inst = ra.get("service.instance.id", "")
                    extra = frozenset((k, v) for k, v in ra.items() if k not in RESOURCE_SKIP)
                    self.resources[(job, inst)].add(extra)
                    for sm in rm.get("scopeMetrics", []):
                        sc = sm.get("scope", {}); self.scopes[(sc.get("name"), sc.get("version"))] += 1
                        for m in sm.get("metrics", []):
                            kind = next(x for x in ("gauge", "sum", "histogram", "exponentialHistogram", "summary") if x in m)
                            body = m[kind]
                            meta = self.meta.setdefault(m["name"], {"kind": kind, "unit": m.get("unit", ""), "description": m.get("description", ""),
                                                                      "monotonic": body.get("isMonotonic"), "temporality": body.get("aggregationTemporality"),
                                                                      "ptype": attrs(m.get("metadata")).get("prometheus.type"), "start_ts": 0, "points": 0})
                            if len(m.get("description", "")) > len(meta["description"]): meta["description"] = m.get("description", "")
                            for dp in body.get("dataPoints", []):
                                self.points += 1
                                t = int(dp["timeUnixNano"]) // 1_000_000
                                self.first_ts = t if self.first_ts is None else min(self.first_ts, t)
                                self.last_ts = t if self.last_ts is None else max(self.last_ts, t)
                                meta["points"] += 1
                                if int(dp.get("startTimeUnixNano", 0)) > 0: meta["start_ts"] += 1
                                if not (lo_ms < t <= hi_ms): continue
                                self.points_in_window += 1
                                la = attrs(dp.get("attributes"))
                                rep = la.pop("prometheus_replica", None) if strip_external else None
                                if strip_external: la.pop("prometheus", None)
                                if job: la["job"] = job
                                if inst: la["instance"] = inst
                                if not job and not inst: self.empty_resource_points += 1
                                k = key_of(m["name"], la)
                                self.names[m["name"]] += 1
                                if rep: self.replica[k][rep] += 1
                                if int(dp.get("flags", 0)) & 1: self.flags[k] += 1
                                if kind in ("gauge", "sum"):
                                    if rep: self.by_rep[rep][k][t].append(dp_value(dp))
                                    else: self.floats[k][t].append(dp_value(dp))
                                else:
                                    self.hists[k][t] = dp
                                for ex in dp.get("exemplars", []) or []:
                                    self.exemplars[k].append(ex)

# ---------------------------------------------------------------- float comparison
def compare_floats(src, dump, replica_filter=None):
    """src: key->{ts:v}; dump: key->{ts:[v]}. Returns a stats dict and example lists."""
    st = Counter(); ex = defaultdict(list)
    src_keys = set(src); dump_keys = set(dump)
    st["series_source"] = len(src_keys); st["series_dump"] = len(dump_keys)
    only_src = src_keys - dump_keys; only_dump = dump_keys - src_keys
    st["series_only_source"] = len(only_src); st["series_only_dump"] = len(only_dump)
    ex["series_only_source"] = sorted(only_src)[:2000]
    ex["series_only_dump"] = sorted(only_dump)[:2000]
    st["series_exact"] = 0
    for k in src_keys & dump_keys:
        s = src[k]; d = dump[k]
        st["samples_source"] += len(s)
        exact = True
        for t, v in s.items():
            dv = d.get(t)
            if not dv:
                st["missing_in_dump"] += 1; exact = False
                if len(ex["missing_in_dump"]) < 50: ex["missing_in_dump"].append((k, t, v))
            else:
                if not same(v, dv[0]):
                    st["value_mismatch"] += 1; exact = False
                    if len(ex["value_mismatch"]) < 50: ex["value_mismatch"].append((k, t, v, dv))
                else:
                    st["samples_equal"] += 1
                if len(dv) > 1:
                    st["duplicates_in_dump"] += len(dv) - 1; exact = False
                    if not all(same(dv[0], x) for x in dv): st["duplicates_with_different_value"] += 1
                    if len(ex["duplicates_in_dump"]) < 30: ex["duplicates_in_dump"].append((k, t, dv))
        for t, dv in d.items():
            if t not in s:
                for x in dv:
                    if math.isnan(x):
                        st["extra_nan_in_dump"] += 1
                        if len(ex["extra_nan_in_dump"]) < 30: ex["extra_nan_in_dump"].append((k, t))
                    else:
                        st["extra_in_dump"] += 1; exact = False
                        if len(ex["extra_in_dump"]) < 30: ex["extra_in_dump"].append((k, t, x))
        if exact: st["series_exact"] += 1
    st["samples_dump_matched_series"] = sum(sum(len(v) for v in dump[k].values()) for k in src_keys & dump_keys)
    return st, ex

# ---------------------------------------------------------------- histogram comparison
def api_buckets(h):
    """Prometheus API histogram -> (count, sum, {(lower, upper): count})"""
    b = {}
    for rule, lo, hi, c in h.get("buckets", []):
        b[(fnum(lo), fnum(hi))] = fnum(c)
    return fnum(h["count"]), fnum(h["sum"]), b

def close(a, b, rel=1e-9):
    if a == b: return True
    if math.isinf(a) or math.isinf(b): return a == b
    return abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)

def exp_buckets(dp):
    """OTLP exponential histogram dp -> {(lower, upper): count} incl. the zero bucket"""
    scale = int(dp.get("scale", 0)); base = 2 ** (2 ** -scale)
    out = {}
    for sign, side in ((1, "positive"), (-1, "negative")):
        s = dp.get(side, {}) or {}
        off = int(s.get("offset", 0))
        for i, c in enumerate(s.get("bucketCounts", []) or []):
            c = int(c)
            if c == 0: continue
            idx = off + i
            lo = base ** idx; hi = base ** (idx + 1)
            if sign > 0: out[(lo, hi)] = out.get((lo, hi), 0) + c
            else: out[(-hi, -lo)] = out.get((-hi, -lo), 0) + c
    zc = int(dp.get("zeroCount", 0))
    if zc: out[("zero", fnum(dp.get("zeroThreshold", 0)))] = zc
    return out

def explicit_buckets(dp):
    bounds = [fnum(x) for x in dp.get("explicitBounds", [])]
    counts = [int(x) for x in dp.get("bucketCounts", [])]
    out = {}
    prev = float("-inf")
    for i, c in enumerate(counts):
        hi = bounds[i] if i < len(bounds) else float("inf")
        if c: out[(prev, hi)] = c
        prev = hi
    return out

def compare_hists(src, dump):
    st = Counter(); ex = defaultdict(list)
    src_keys = set(src); dump_keys = set(dump)
    st["series_source"] = len(src_keys); st["series_dump"] = len(dump_keys)
    st["series_only_source"] = len(src_keys - dump_keys); st["series_only_dump"] = len(dump_keys - src_keys)
    ex["series_only_source"] = sorted(src_keys - dump_keys)[:200]; ex["series_only_dump"] = sorted(dump_keys - src_keys)[:200]
    for k in src_keys & dump_keys:
        s = src[k]; d = dump[k]
        for t, h in s.items():
            st["points_source"] += 1
            dp = d.get(t)
            if dp is None:
                st["missing_in_dump"] += 1
                if len(ex["missing_in_dump"]) < 20: ex["missing_in_dump"].append((k, t)); continue
            cnt, sm, ab = api_buckets(h)
            dcnt = fnum(dp.get("count", 0)); dsum = fnum(dp.get("sum", 0))
            ok = close(cnt, dcnt) and close(sm, dsum)
            if "scale" in dp or "positive" in dp or "negative" in dp:
                st["exponential_points"] += 1
                db = exp_buckets(dp)
                zero = [(kk, v) for kk, v in db.items() if kk[0] == "zero"]
                db = {kk: v for kk, v in db.items() if kk[0] != "zero"}
                # the API reports the zero bucket as (-threshold, threshold)
                for (lo, hi), c in list(ab.items()):
                    if lo < 0 < hi or (lo == 0 and hi == 0) or (lo <= 0 and hi >= 0 and not any(close(lo, x[0]) and close(hi, x[1]) for x in db)):
                        if zero and close(zero[0][1], c): del ab[(lo, hi)]; zero = []
                bok = len(ab) == len(db) and all(any(close(lo, dlo) and close(hi, dhi) and c == dc for (dlo, dhi), dc in db.items()) for (lo, hi), c in ab.items())
                ok = ok and bok and not zero
            else:
                st["explicit_points"] += 1
                db = explicit_buckets(dp)
                bok = len(ab) == len(db) and all(any(close(hi, dhi) and c == dc for (dlo, dhi), dc in db.items()) for (lo, hi), c in ab.items())
                ok = ok and bok
            if ok: st["points_equal"] += 1
            else:
                st["points_mismatch"] += 1
                if len(ex["mismatch"]) < 20: ex["mismatch"].append((k, t, h, {x: dp.get(x) for x in ("count", "sum", "scale", "zeroCount", "zeroThreshold", "positive", "negative", "bucketCounts", "explicitBounds", "flags")}))
        for t in d:
            if t not in s:
                dp = d[t]
                if int(dp.get("flags", 0)) & 1: st["extra_norecordedvalue_in_dump"] += 1
                else:
                    st["extra_in_dump"] += 1
                    if len(ex["extra_in_dump"]) < 20: ex["extra_in_dump"].append((k, t))
    return st, ex

# ---------------------------------------------------------------- counters
def counter_map(name):
    d = load_json(name); out = {}
    if not d or d.get("status") != "success": return out
    for r in d["data"]["result"]:
        m = dict(r["metric"]); nm = m.pop("__name__")
        out[(nm, tuple(sorted(m.items())))] = fnum(r["value"][1])
    return out

def deltas(start, end, keep=lambda k: True):
    out = {}
    for k, v in end.items():
        if not keep(k): continue
        s = start.get(k)
        out[k] = (s, v, None if s is None else v - s)
    return out

def md_table(rows, header):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows: out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)

def fmtk(k):
    name, labels = k
    return name + "{" + ",".join(f'{a}="{b}"' for a, b in labels if a not in ("job", "instance")) + "}" + " " + " ".join(f"{a}={b}" for a, b in labels if a in ("job", "instance"))

# ---------------------------------------------------------------- main
W = windows()
report = {}
for w, (lo, hi) in W.items():
    md = [f"# Window {w}: ({lo}, {hi}] = {(hi-lo)//60} min\n"]
    res = {}
    # ---- typed path
    tf, th = load_source(f"typed-source-w{w}.json", lo, hi)
    td = Dump(os.path.join(RAW, "typed-dump.jsonl"), lo, hi, strip_external=False)
    st, ex = compare_floats(tf, td.floats)
    hst, hex_ = compare_hists(th, td.hists)
    res["typed"] = {"floats": dict(st), "hists": dict(hst), "dump_points_in_window": td.points_in_window, "dump_points_total": td.points,
                    "dump_lines": td.lines, "bad_lines": td.bad_lines, "norecordedvalue_series": len(td.flags), "norecordedvalue_points": sum(td.flags.values()),
                    "scopes": {str(k): v for k, v in td.scopes.items()}, "empty_resource_points": td.empty_resource_points}
    md.append("## Typed path (Prometheus main with metadata -> contrib nightly receiver)\n")
    md.append(md_table([[k, v] for k, v in sorted(st.items())], ["float series / samples", "count"]))
    md.append("\nSeries only in the source (not emitted), by family:\n")
    fam = Counter(k[0] for k in ex["series_only_source"])
    md.append(md_table(sorted(fam.items(), key=lambda x: -x[1])[:60], ["family", "series"]))
    md.append("\nSeries only in the dump (no TSDB counterpart), by family:\n")
    fam2 = Counter(k[0] for k in ex["series_only_dump"])
    md.append(md_table(sorted(fam2.items(), key=lambda x: -x[1])[:60], ["family", "series"]))
    for cat in ("missing_in_dump", "value_mismatch", "duplicates_in_dump", "extra_in_dump", "extra_nan_in_dump"):
        if ex[cat]:
            md.append(f"\nExamples `{cat}` ({len(ex[cat])} shown):\n")
            md.append("\n".join("- " + fmtk(e[0]) + " " + json.dumps(e[1:], default=str) for e in ex[cat][:12]))
    md.append("\n### Native histograms and NHCB\n")
    md.append(md_table([[k, v] for k, v in sorted(hst.items())], ["histogram series / points", "count"]))
    if hex_["mismatch"]:
        md.append("\nMismatch examples:\n")
        md.append("\n".join("- " + fmtk(e[0]) + " " + json.dumps(e[1:], default=str)[:1200] for e in hex_["mismatch"][:6]))
    if hex_["series_only_source"]:
        md.append("\nHistogram series only in the source: " + ", ".join(sorted(set(k[0] for k in hex_["series_only_source"]))))
    md.append("\nNoRecordedValue flagged points in the dump: %d on %d series" % (sum(td.flags.values()), len(td.flags)))
    if td.flags:
        md.append("\n".join("- " + fmtk(k) + f" x{v}" for k, v in list(td.flags.items())[:10]))
    # metadata (typed only)
    if w == 1:
        meta_src = load_json("typed-source-metadata.json") or {}
        rows = []
        for name in sorted(td.meta):
            m = td.meta[name]
            src = (meta_src.get("data", {}) or {}).get(name) or (meta_src.get("data", {}) or {}).get(re.sub(r"_(total|bucket|sum|count|created)$", "", name)) or [{}]
            rows.append([name, src[0].get("type", "?"), src[0].get("unit", ""), m["kind"], m["monotonic"], m["ptype"], m["unit"], (m["description"] or "")[:40].replace("|", "/"), f'{m["start_ts"]}/{m["points"]}'])
        res["typed"]["metadata"] = rows
        md.append("\n### Metadata: Prometheus type/unit -> OTLP kind/monotonic/prometheus.type/unit, start timestamps set (points with startTimeUnixNano / points)\n")
        md.append(md_table([r for r in rows if r[0].startswith(("corr_", "avalanche_", "up", "scrape_", "go_gc_duration", "go_gc_heap_allocs_by_size", "prometheus_remote_storage_samples_total", "prometheus_http_request_duration_seconds", "otelcol_receiver_accepted"))], ["metric", "src type", "src unit", "kind", "monotonic", "prometheus.type", "unit", "description", "start ts"]))
        md.append("\nKinds over all %d families (src type, kind, monotonic -> families): %s" % (len(rows), json.dumps({str(k): v for k, v in Counter((r[1], r[3], str(r[4])) for r in rows).items()})))
        md.append("\nScopes: " + json.dumps({str(k): v for k, v in td.scopes.items()}))
        # exemplars
        src_ex = load_json("typed-source-exemplars.json") or {}
        src_set = defaultdict(set)
        for r in src_ex.get("data", []) or []:
            m = dict(r["seriesLabels"]); nm = m.pop("__name__", "")
            for e in r["exemplars"]:
                if not (lo * 1000 < int(round(float(e["timestamp"]) * 1000)) <= hi * 1000): continue
                src_set[key_of(nm, m)].add((e["labels"].get("trace_id", ""), e["labels"].get("span_id", ""), fnum(e["value"]), int(round(float(e["timestamp"]) * 1000)), tuple(sorted((a, b) for a, b in e["labels"].items() if a not in ("trace_id", "span_id")))))
        dump_set = defaultdict(set)
        for k, lst in td.exemplars.items():
            for e in lst:
                fa = attrs(e.get("filteredAttributes"))
                dump_set[k].add((e.get("traceId", ""), e.get("spanId", ""), dp_value(e), int(e.get("timeUnixNano", 0)) // 1_000_000, tuple(sorted(fa.items()))))
        exrows = []
        for k in sorted(set(src_set) | set(dump_set)):
            s = src_set.get(k, set()); d = dump_set.get(k, set())
            exrows.append([fmtk(k), len(s), len(d), len(s & d), len(s - d), len(d - s)])
        res["typed"]["exemplars"] = exrows
        md.append("\n### Exemplars (window 1): source exemplar storage vs dump, matched on trace id, span id, value, timestamp and the other labels\n")
        md.append(md_table(exrows, ["series", "source", "dump", "equal", "only source", "only dump"]))
        if td.exemplars:
            k0 = next(iter(td.exemplars)); md.append("\nFirst dump exemplar: `" + json.dumps(td.exemplars[k0][0]) + "`")
        for r in (src_ex.get("data", []) or [])[:1]:
            md.append("First source exemplar: `" + json.dumps(r["exemplars"][0]) + "`")
    # ---- production path (per replica, product collector and contrib collector)
    for dumpname in ("prod", "prod-contrib"):
        pd = Dump(os.path.join(RAW, f"{dumpname}-dump.jsonl"), lo, hi, strip_external=True)
        res[dumpname] = {"dump_points_in_window": pd.points_in_window, "dump_points_total": pd.points, "lines": pd.lines, "bad_lines": pd.bad_lines,
                         "empty_resource_points": pd.empty_resource_points, "scopes": {str(k): v for k, v in pd.scopes.items()},
                         "norecordedvalue_points": sum(pd.flags.values())}
        md.append(f"\n## Production path, dump of `{dumpname}` (platform Prometheus 3.13.2, both replicas)\n")
        for r in (0, 1):
            sf, sh = load_source(f"prod{r}-source-w{w}.json", lo, hi)
            # the dump keeps both replicas under the same series key: split by the replica tag
            rep = f"prometheus-k8s-{r}"
            st, ex = compare_floats(sf, pd.by_rep.get(rep, {}))
            st["points_without_replica_label"] = sum(len(v) for pts in pd.floats.values() for v in pts.values())
            res[dumpname][f"replica{r}"] = dict(st)
            md.append(f"### replica {rep}\n")
            md.append(md_table([[k, v] for k, v in sorted(st.items())], ["float series / samples", "count"]))
            fam = Counter(k[0] for k in ex["series_only_source"]); fam2 = Counter(k[0] for k in ex["series_only_dump"])
            if fam: md.append("\nonly in source by family: " + json.dumps(dict(fam.most_common(20))))
            if fam2: md.append("\nonly in dump by family: " + json.dumps(dict(fam2.most_common(20))))
            for cat in ("missing_in_dump", "value_mismatch", "duplicates_in_dump", "extra_in_dump", "extra_nan_in_dump"):
                if ex[cat]:
                    md.append(f"\nExamples `{cat}`:\n" + "\n".join("- " + fmtk(e[0]) + " " + json.dumps(e[1:], default=str)[:300] for e in ex[cat][:8]))
        md.append("\nMetadata on the production path (kind, prometheus.type, unit, has description -> families): " + json.dumps({str(k): v for k, v in Counter((m["kind"], m["ptype"], m["unit"], bool(m["description"])) for m in pd.meta.values()).items()}))
        md.append("Points with startTimeUnixNano: %d of %d" % (sum(m["start_ts"] for m in pd.meta.values()), sum(m["points"] for m in pd.meta.values())))
        md.append("Points with an empty resource (no job/instance, e.g. ALERTS): %d" % pd.empty_resource_points)
        split = {k: v for k, v in pd.resources.items() if len(v) > 1}
        md.append("Resource splits (job/instance pairs seen with more than one resource attribute set): %d of %d pairs" % (len(split), len(pd.resources)))
        res[dumpname]["resource_pairs"] = len(pd.resources); res[dumpname]["resource_splits"] = len(split)
        md.append("Scopes: " + json.dumps({str(k): v for k, v in pd.scopes.items()}))
    # ---- resource splits on the typed path
    split = {k: v for k, v in td.resources.items() if len(v) > 1}
    md.append("\nTyped path resource pairs: %d, splits: %d; extra resource attributes seen: %s" % (len(td.resources), len(split), json.dumps(sorted(set(a for s in td.resources.values() for fs in s for a, _ in fs)))))
    # ---- counters
    md.append("\n## Counters at the window boundaries (value at start, at end, delta)\n")
    rows = []
    for src in ("typed", "prod0", "prod1"):
        a = counter_map(f"{src}-counters-w{w}-start.json"); b = counter_map(f"{src}-counters-w{w}-end.json")
        for k, (s, e, dlt) in sorted(deltas(a, b).items()):
            labels = dict(k[1]); rn = labels.get("remote_name", "")
            if k[0].startswith("prometheus_remote_storage") and not rn: continue
            rows.append([src, k[0], rn, s, e, dlt])
    a = counter_map(f"otelcol-counters-w{w}-start.json"); b = counter_map(f"otelcol-counters-w{w}-end.json")
    for k, (s, e, dlt) in sorted(deltas(a, b).items()):
        labels = dict(k[1]); col = labels.get("instance", "").split("-collector-monitoring")[0]
        rows.append(["otelcol " + col, k[0], labels.get("receiver", labels.get("exporter", "")), s, e, dlt])
    res["counters"] = rows
    md.append(md_table(rows, ["where", "metric", "name", "start", "end", "delta"]))
    # ---- sink vs source per family (all families of each sender), from family-counts.py output
    md.append("\n## Sink (Prometheus with the OTLP receiver) vs the senders' TSDB, sample counts per metric family over the window\n")
    def fam_compare(src, sink, label):
        eq = 0; diff = {}; missing = {}; total_src = 0; total_sink = 0
        for name, c in src.items():
            total_src += c
            sc = sink.get(name)
            if sc is None: missing[name] = c
            elif sc == c: eq += 1; total_sink += sc
            else: diff[name] = sc - c; total_sink += sc
        extra = {n: c for n, c in sink.items() if n not in src}
        res[f"family_{label}"] = {"families_source": len(src), "equal": eq, "missing_in_sink": missing, "diff": diff, "extra_in_sink": extra, "samples_source": total_src, "samples_sink_matched": total_sink}
        return [label, len(src), total_src, eq, len(missing), len(diff), len(extra), json.dumps(dict(sorted(diff.items(), key=lambda x: -abs(x[1]))[:10])), json.dumps(dict(list(missing.items())[:8])), json.dumps(dict(list(extra.items())[:8]))]
    rows = []
    sinkfam = load_fam(f"sink-family-counts-w{w}.json")
    for r in (0, 1):
        rep = f"prometheus-k8s-{r}"
        srcfam = load_fam(f"prod{r}-family-counts-w{w}.json")
        src = {n: v.get("", 0) for n, v in srcfam.items()}
        sink = {n: v[rep] for n, v in sinkfam.items() if rep in v}
        rows.append(fam_compare(src, sink, rep))
    typedfam = load_fam(f"typed-family-counts-w{w}.json")
    sinktyped = load_fam(f"sink-typed-family-counts-w{w}.json")
    emitted = set(td.meta)
    missing_class = Counter(); missing_list = defaultdict(list)
    for job in ("prometheus", "avalanche", "exemplar-app", "stale-app", "otelcol"):
        src = {n: v[job] for n, v in typedfam.items() if job in v}
        sink = {n: v[job] for n, v in sinktyped.items() if job in v}
        rows.append(fam_compare(src, sink, "typed job=" + job))
        for n in res["family_typed job=" + job]["missing_in_sink"]:
            cls = "emitted by the collector as a histogram, stored by the sink as classic series" if n in emitted else "not emitted by the collector"
            missing_class[cls] += 1; missing_list[cls].append(n)
    res["typed_missing_in_sink_classes"] = {k: sorted(set(v)) for k, v in missing_list.items()}
    md.append(md_table(rows, ["sender", "families", "samples (source)", "families equal", "missing in sink", "different", "extra in sink", "largest differences (sink - source)", "missing", "extra"]))
    md.append("\nTyped families missing in the sink, classified: " + json.dumps({k: len(set(v)) for k, v in missing_list.items()}))
    for k, v in missing_list.items():
        md.append(f"- {k}: " + ", ".join(sorted(set(v))))
    report[f"w{w}"] = res
    with open(os.path.join(D, f"compare-w{w}.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    print(f"wrote compare-w{w}.md")
with open(os.path.join(D, "compare.json"), "w") as f:
    json.dump(report, f, indent=1, default=str)
print("wrote compare.json")
