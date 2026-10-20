#!/usr/bin/env python3
"""Summarise the audit log events pulled per phase by scripts/run-scale-ladder.sh (raw/audit/<tag>.jsonl).

usage: scripts/audit-scale.py <results dir>
writes raw/audit-requests.csv (tag, user, verb, resource, requests: one row per phase, client, verb and resource)
and raw/audit-lists.csv (one row per LIST or initial-events WATCH: tag, user, resource, start, duration_s, code)
"""
import csv, glob, json, os, sys
from datetime import datetime, timezone
USERS = {"system:serviceaccount:otel-platform-metrics:otel-k8scluster": "otel-k8scluster",
         "system:serviceaccount:openshift-monitoring:kube-state-metrics": "kube-state-metrics"}
d = sys.argv[1]
def ts(s): return datetime.strptime(s[:26].rstrip("Z"), "%Y-%m-%dT%H:%M:%S.%f" if "." in s[:26] else "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
counts, lists, seen = {}, [], set()
for f in sorted(glob.glob(os.path.join(d, "raw", "audit", "*.jsonl"))):
    tag = os.path.basename(f)[:-6]
    for line in open(f, errors="replace"):
        try: e = json.loads(line)
        except ValueError: continue
        u = USERS.get((e.get("user") or {}).get("username"))
        if not u: continue
        verb = e.get("verb"); res = (e.get("objectRef") or {}).get("resource") or e.get("requestURI", "")[:40]
        uri = e.get("requestURI", ""); stage = e.get("stage")
        initial = verb == "watch" and "sendInitialEvents=true" in uri
        if (tag, e["auditID"]) not in seen:  # one request = one row whichever stages were captured
            seen.add((tag, e["auditID"])); key = (tag, u, verb + ("+initial" if initial else ""), res); counts[key] = counts.get(key, 0) + 1
        # a LIST is one event (ResponseComplete, with its duration); an initial-events watch is recorded at its start, the
        # streaming of the initial events is not in the audit log (apiserver_watch_list_duration_seconds has it)
        if (verb == "list" and stage == "ResponseComplete") or (initial and stage == "ResponseStarted"):
            t0 = ts(e["requestReceivedTimestamp"]); t1 = ts(e["stageTimestamp"])
            lists.append((tag, u, res, int(t0), round(t1 - t0, 3) if verb == "list" else "", (e.get("responseStatus") or {}).get("code"), verb + ("+initial" if initial else "")))
os.makedirs(os.path.join(d, "raw"), exist_ok=True)
with open(os.path.join(d, "raw", "audit-requests.csv"), "w") as fh:
    w = csv.writer(fh); w.writerow(["tag", "user", "verb", "resource", "requests"])
    for (tag, u, verb, res), n in sorted(counts.items()): w.writerow([tag, u, verb, res, n])
with open(os.path.join(d, "raw", "audit-lists.csv"), "w") as fh:
    w = csv.writer(fh); w.writerow(["tag", "user", "resource", "start", "duration_s", "code", "verb"])
    for row in sorted(lists): w.writerow(row)
print(f"{len(counts)} request rows, {len(lists)} list rows")
