#!/usr/bin/env python3
"""Replace cluster-specific identifiers in the files that are committed: IPv4 addresses, the AWS
node names, the cluster id and the API server host, so that no address or hostname of the test
cluster ends up in the repository. Applied in place to every file given on the command line;
the mapping is stable within one run (same address -> same placeholder).
usage: scripts/scrub.py <file>...
"""
import re, sys
ip_map, node_map = {}, {}
def ip(m):
    return ip_map.setdefault(m.group(0), "IP-%d" % (len(ip_map) + 1))
def node(m):
    return node_map.setdefault(m.group(0), "node-%d" % (len(node_map) + 1))
pats = [
    (re.compile(r"\bip-\d+-\d+-\d+-\d+\.[a-z0-9-]+\.compute\.internal"), node),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), ip),
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"), lambda m: "UUID"),
    (re.compile(r"\b[a-z0-9.-]+\.(?:devcluster\.openshift\.com|openshiftapps\.com|redhat\.com)\b"), lambda m: "HOST"),
]
for path in sys.argv[1:]:
    with open(path, encoding="utf-8", errors="surrogateescape") as f:
        s = f.read()
    n = 0
    for pat, fn in pats:
        s, k = pat.subn(fn, s); n += k
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(s)
    print(f"{path}: {n} replacements")
