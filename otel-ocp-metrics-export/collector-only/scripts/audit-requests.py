#!/usr/bin/env python3
"""Count the kube-apiserver requests of two service accounts per phase from the audit logs of the control plane nodes.

usage: scripts/audit-requests.py <results dir> <audit log file>...   (writes <results dir>/raw/audit-requests.csv)
Phases and their windows come from <results dir>/runs.json; one row per phase, user, verb and resource with the
number of ResponseComplete events (a watch counts once when it ends, a list once per list).
"""
import csv, json, os, sys
from datetime import datetime, timezone
USERS = {"system:serviceaccount:otel-platform-metrics:otel-k8scluster": "otel-k8scluster",
         "system:serviceaccount:openshift-monitoring:kube-state-metrics": "kube-state-metrics"}
d = sys.argv[1]; runs = json.load(open(os.path.join(d, "runs.json")))
phases = [(r["label"].split(":")[0], r["start"], r["end"]) for r in runs if r["kind"] != "timeline"]
counts = {}
seen = set()
for f in sys.argv[2:]:
    with open(f, errors="replace") as fh:
        for line in fh:
            if '"ResponseComplete"' not in line or "serviceaccount:" not in line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                continue
            u = USERS.get((e.get("user") or {}).get("username"))
            if not u or e.get("auditID") in seen:
                continue
            seen.add(e["auditID"])
            ts = datetime.strptime(e["requestReceivedTimestamp"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
            for name, start, end in phases:
                if start <= ts <= end:
                    key = (name, u, e.get("verb"), (e.get("objectRef") or {}).get("resource") or e.get("requestURI", "")[:40])
                    counts[key] = counts.get(key, 0) + 1
out = os.path.join(d, "raw", "audit-requests.csv"); os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w") as fh:
    w = csv.writer(fh); w.writerow(["phase", "user", "verb", "resource", "requests"])
    for (name, u, verb, res), n in sorted(counts.items()):
        w.writerow([name, u, verb, res, n])
print(f"{len(counts)} rows in {out} from {len(seen)} events")
