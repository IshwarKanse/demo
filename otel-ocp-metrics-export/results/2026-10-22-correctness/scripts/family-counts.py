#!/usr/bin/env python3
"""Sample counts per metric family over a window, one query per family (Prometheus 3 rejects
count_over_time over several families when their label sets collide after the name is dropped).
usage: family-counts.py <port> <outfile> <window seconds> <end epoch> [<extra matcher>] [<by label>]
Writes {"family": {"<by value or ''>": count}} and prints the total.
"""
import json, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
port, out, win, end = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
matcher = sys.argv[5] if len(sys.argv) > 5 else ""
by = sys.argv[6] if len(sys.argv) > 6 else ""
base = f"http://localhost:{port}/api/v1/"
def get(path, params):
    with urllib.request.urlopen(base + path + "?" + urllib.parse.urlencode(params), timeout=600) as r:
        return json.load(r)
names = get("label/__name__/values", {"match[]": "{__name__=~\".+\"" + ("," + matcher if matcher else "") + "}", "start": str(int(end) - int(win)), "end": end})["data"]
def one(name):
    sel = '{__name__="%s"%s}' % (name.replace('\\', '\\\\').replace('"', '\\"'), ("," + matcher) if matcher else "")
    q = ("sum by (%s) " % by if by else "sum") + "(count_over_time(%s[%ss]))" % (sel, win)
    try:
        d = get("query", {"query": q, "time": end})
        if d["status"] != "success":
            return name, {"error": d.get("error")}
        return name, {r["metric"].get(by, ""): float(r["value"][1]) for r in d["data"]["result"]}
    except Exception as e:
        return name, {"error": str(e)}
res = {}
with ThreadPoolExecutor(16) as ex:
    for name, v in ex.map(one, names):
        res[name] = v
json.dump(res, open(out, "w"))
tot = {}
for v in res.values():
    for k, c in v.items():
        if k != "error": tot[k] = tot.get(k, 0) + c
print(out, len(names), "families, totals", tot, "errors", sum(1 for v in res.values() if "error" in v))
