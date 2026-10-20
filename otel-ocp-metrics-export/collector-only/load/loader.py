#!/usr/bin/env python3
"""In-cluster object loader for the k8s_cluster receiver scale ladder (runs as a Job, see load/loader-driver.yaml).

The inventory is made of units; one unit is one namespace `otel-load-NNNN` with 1,000 created objects in the
proportions of a busy cluster (config maps and secrets dominate): 400 config maps, 263 secrets, 150 deployments at
0 replicas (one ReplicaSet each, no pod), 100 headless services (one Endpoints and one EndpointSlice each), 50
suspended jobs, 30 suspended cron jobs, 6 resource quotas and the namespace itself. The first 10 namespaces also get
30 horizontal pod autoscalers each (300 in all, a fixed control plane cost across the ladder) and the first unit
creates 20 cluster resource quotas (counting PVCs, which nothing creates: a quota on config maps would make every
config map create an optimistic update of 20 quota statuses and a flood of 409 conflicts under parallel load). Objects are POSTed by parallel workers over keep-alive connections with the
service account token of the pod; an existing object (409) counts as present, 429/5xx are retried.

usage (inside the pod):
  loader.py create   --from A --to B [--workers 24]   creates the units [A, B)
  loader.py delete   --from A --to B --kind deployments   deletes one kind in the units [A, B) (churn)
  loader.py recreate --from A --to B --kind deployments   recreates one kind in the units [A, B) (churn)
  loader.py cleanup  --from A --to B                      deletes the namespaces of the units and the cluster resource quotas
Prints a progress line every 5 s and a final JSON line with the counts, the duration and the request rate.
"""
import argparse, base64, http.client, json, os, queue, ssl, sys, threading, time

PART_OF = "otel-load-objects"
PER_UNIT = {"configmaps": 400, "secrets": 263, "deployments": 150, "services": 100, "jobs": 50, "cronjobs": 30, "quotas": 6}
HPA_UNITS, HPA_PER_UNIT, CRQS = 10, 30, 20
KINDS = {  # kind -> (API path prefix, resource, label value)
    "configmaps": ("/api/v1", "configmaps", "configmap"),
    "secrets": ("/api/v1", "secrets", "secret"),
    "deployments": ("/apis/apps/v1", "deployments", "deployment"),
    "services": ("/api/v1", "services", "service"),
    "jobs": ("/apis/batch/v1", "jobs", "job"),
    "cronjobs": ("/apis/batch/v1", "cronjobs", "cronjob"),
    "quotas": ("/api/v1", "resourcequotas", "quota"),
    "hpas": ("/apis/autoscaling/v2", "horizontalpodautoscalers", "hpa"),
}
SA = "/var/run/secrets/kubernetes.io/serviceaccount"


def ns_name(u): return f"otel-load-{u:04d}"


def meta(name, ns, kind):
    m = {"name": name, "labels": {"app.kubernetes.io/part-of": PART_OF, "load-kind": kind}}
    if ns: m["namespace"] = ns
    return m


POD_TEMPLATE = {
    "securityContext": {"runAsNonRoot": True, "seccompProfile": {"type": "RuntimeDefault"}},
    "containers": [{"name": "pause", "image": "registry.access.redhat.com/ubi9/ubi-minimal:latest",
                    "command": ["sleep", "infinity"],
                    "securityContext": {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}},
                    "resources": {"requests": {"cpu": "1m", "memory": "8Mi"}, "limits": {"memory": "32Mi"}}}]}


def objects(u, kind):
    """Yields (path, body) for one kind of one unit."""
    ns = ns_name(u); prefix, resource, label = KINDS[kind]; path = f"{prefix}/namespaces/{ns}/{resource}"
    if kind == "hpas":
        n = HPA_PER_UNIT if u < HPA_UNITS else 0
    else:
        n = PER_UNIT[kind]
    for i in range(n):
        name = f"load-{label}-{i:04d}"
        if kind == "configmaps":
            body = {"apiVersion": "v1", "kind": "ConfigMap", "metadata": meta(name, ns, label),
                    "data": {f"key{k}": f"{u:04d}-{i:04d}-" + "x" * 120 for k in range(4)}}
        elif kind == "secrets":
            body = {"apiVersion": "v1", "kind": "Secret", "metadata": meta(name, ns, label), "type": "Opaque",
                    "data": {"username": base64.b64encode(f"user-{u}-{i}".encode()).decode(),
                             "password": base64.b64encode((f"{u:04d}-{i:04d}-" + "p" * 100).encode()).decode()}}
        elif kind == "deployments":
            body = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": meta(name, ns, label),
                    "spec": {"replicas": 0, "selector": {"matchLabels": {"app": name}},
                             "template": {"metadata": {"labels": {"app": name, "app.kubernetes.io/part-of": PART_OF}},
                                          "spec": POD_TEMPLATE}}}
        elif kind == "services":
            body = {"apiVersion": "v1", "kind": "Service", "metadata": meta(name, ns, label),
                    "spec": {"clusterIP": "None", "selector": {"app": f"load-deployment-{i:04d}"},
                             "ports": [{"name": "http", "port": 8080, "targetPort": 8080}]}}
        elif kind == "jobs":
            body = {"apiVersion": "batch/v1", "kind": "Job", "metadata": meta(name, ns, label),
                    "spec": {"suspend": True, "backoffLimit": 0,
                             "template": {"metadata": {"labels": {"app.kubernetes.io/part-of": PART_OF}},
                                          "spec": dict(POD_TEMPLATE, restartPolicy="Never",
                                                       containers=[dict(POD_TEMPLATE["containers"][0], name="run", command=["true"])])}}}
        elif kind == "cronjobs":
            body = {"apiVersion": "batch/v1", "kind": "CronJob", "metadata": meta(name, ns, label),
                    "spec": {"schedule": "0 0 1 1 *", "suspend": True,
                             "jobTemplate": {"spec": {"template": {"spec": dict(POD_TEMPLATE, restartPolicy="Never",
                                                                               containers=[dict(POD_TEMPLATE["containers"][0], name="run", command=["true"])])}}}}}
        elif kind == "quotas":
            body = {"apiVersion": "v1", "kind": "ResourceQuota", "metadata": meta(name, ns, label),
                    "spec": {"hard": {"count/secrets": "100000"}}}
        elif kind == "hpas":
            body = {"apiVersion": "autoscaling/v2", "kind": "HorizontalPodAutoscaler", "metadata": meta(name, ns, label),
                    "spec": {"scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": f"load-deployment-{i:04d}"},
                             "minReplicas": 1, "maxReplicas": 2,
                             "metrics": [{"type": "Resource", "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": 90}}}]}}
        yield path, body


def namespace_body(u):
    return {"apiVersion": "v1", "kind": "Namespace",
            "metadata": {"name": ns_name(u), "labels": {"app.kubernetes.io/part-of": PART_OF, "load-kind": "namespace", "otel-load": "true"}}}


def crq_body(i):
    return {"apiVersion": "quota.openshift.io/v1", "kind": "ClusterResourceQuota",
            "metadata": meta(f"otel-load-crq-{i:04d}", None, "crq"),
            "spec": {"selector": {"labels": {"matchLabels": {"otel-load": "true"}}}, "quota": {"hard": {"count/persistentvolumeclaims": "1000"}}}}


class Client:
    def __init__(self):
        self.host = os.environ.get("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
        self.port = int(os.environ.get("KUBERNETES_SERVICE_PORT", "443"))
        self.token = open(f"{SA}/token").read().strip()
        self.ctx = ssl.create_default_context(cafile=f"{SA}/ca.crt")
        self.local = threading.local()

    def conn(self, fresh=False):
        c = getattr(self.local, "c", None)
        if c is None or fresh:
            if c is not None:
                try: c.close()
                except Exception: pass
            c = http.client.HTTPSConnection(self.host, self.port, context=self.ctx, timeout=120)
            self.local.c = c
        return c

    def request(self, method, path, body=None):
        """Returns (status, text); retries connection errors, 429 and 5xx with a backoff."""
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        if data is not None: headers["Content-Type"] = "application/json"
        delay = 0.5
        for attempt in range(12):
            try:
                c = self.conn(fresh=attempt > 0)
                c.request(method, path, body=data, headers=headers)
                r = c.getresponse(); text = r.read().decode(errors="replace")
                if r.status == 429 or r.status >= 500 or (r.status == 409 and '"reason":"Conflict"' in text):
                    # 409 Conflict (not AlreadyExists) comes from the quota admission updating a quota status under contention
                    ra = r.getheader("Retry-After")
                    STATS.retry(r.status)
                    time.sleep(float(ra) if ra else delay); delay = min(delay * 2, 10)
                    continue
                return r.status, text
            except (http.client.HTTPException, OSError) as e:
                STATS.retry(f"conn:{type(e).__name__}")
                time.sleep(delay); delay = min(delay * 2, 10)
        return 0, "gave up after retries"


class Stats:
    def __init__(self):
        self.lock = threading.Lock(); self.ok = 0; self.exists = 0; self.errors = 0; self.retries = {}; self.per_kind = {}; self.samples = []

    def done(self, kind, status, text, elapsed):
        with self.lock:
            k = self.per_kind.setdefault(kind, {"ok": 0, "exists": 0, "errors": 0})
            if status in (200, 201, 202): self.ok += 1; k["ok"] += 1
            elif status == 409: self.exists += 1; k["exists"] += 1
            elif status == 404 and "delete" in kind: self.exists += 1; k["exists"] += 1
            else:
                self.errors += 1; k["errors"] += 1
                if self.errors <= 20: print(f"error {status} {kind}: {text[:300]}", file=sys.stderr, flush=True)
            self.samples.append(elapsed)

    def retry(self, why):
        with self.lock: self.retries[str(why)] = self.retries.get(str(why), 0) + 1


STATS = Stats()


def worker(client, q):
    while True:
        item = q.get()
        if item is None: return
        kind, method, path, body = item
        t = time.monotonic(); status, text = client.request(method, path, body)
        STATS.done(kind, status, text, time.monotonic() - t)
        q.task_done()


def run(tasks, workers, label):
    """Runs the (kind, method, path, body) tasks on the worker pool and prints the progress and the final summary."""
    client = Client(); q = queue.Queue(maxsize=workers * 4)
    threads = [threading.Thread(target=worker, args=(client, q), daemon=True) for _ in range(workers)]
    for t in threads: t.start()
    start = time.monotonic(); last = start; total = 0
    for task in tasks:
        q.put(task); total += 1
        if time.monotonic() - last >= 5:
            last = time.monotonic(); n = STATS.ok + STATS.exists + STATS.errors
            print(f"{label}: {n} done ({STATS.errors} errors) in {last - start:.0f} s, {n / (last - start):.0f}/s, retries {STATS.retries}", flush=True)
    q.join()
    for _ in threads: q.put(None)
    secs = time.monotonic() - start; n = STATS.ok + STATS.exists + STATS.errors
    s = sorted(STATS.samples); p = lambda f: round(s[min(len(s) - 1, int(f * len(s)))], 3) if s else None
    print(json.dumps({"label": label, "requests": n, "created_or_deleted": STATS.ok, "already": STATS.exists, "errors": STATS.errors,
                      "seconds": round(secs, 1), "rate": round(n / secs, 1) if secs else None, "workers": workers,
                      "latency_s": {"p50": p(0.5), "p90": p(0.9), "p99": p(0.99)}, "retries": STATS.retries, "per_kind": STATS.per_kind}), flush=True)
    return STATS.errors


def create_tasks(a, kinds, with_ns):
    c = Client()
    if with_ns and a.from_unit == 0:
        for i in range(CRQS):
            status, text = c.request("POST", "/apis/quota.openshift.io/v1/clusterresourcequotas", crq_body(i))
            STATS.done("crqs", status, text, 0)
    for u in range(a.from_unit, a.to_unit):
        if with_ns:
            status, text = c.request("POST", "/api/v1/namespaces", namespace_body(u))  # the namespace first, synchronously
            STATS.done("namespaces", status, text, 0)
        for kind in kinds:
            for path, body in objects(u, kind):
                yield kind, "POST", path, body


def delete_tasks(a, kinds):
    for u in range(a.from_unit, a.to_unit):
        for kind in kinds:
            prefix, resource, label = KINDS[kind]
            yield f"delete-{kind}", "DELETE", f"{prefix}/namespaces/{ns_name(u)}/{resource}?labelSelector=load-kind%3D{label}", {"propagationPolicy": "Background"}


def cleanup_tasks(a):
    if a.from_unit == 0:
        yield "delete-crqs", "DELETE", f"/apis/quota.openshift.io/v1/clusterresourcequotas?labelSelector=app.kubernetes.io/part-of%3D{PART_OF}", None
    for u in range(a.from_unit, a.to_unit):
        yield "delete-namespaces", "DELETE", f"/api/v1/namespaces/{ns_name(u)}", None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["create", "delete", "recreate", "cleanup"])
    p.add_argument("--from", dest="from_unit", type=int, required=True); p.add_argument("--to", dest="to_unit", type=int, required=True)
    p.add_argument("--kind", default=""); p.add_argument("--workers", type=int, default=24)
    a = p.parse_args()
    kinds = [k for k in a.kind.split(",") if k] or list(PER_UNIT) + ["hpas"]
    if a.command == "create":
        tasks = create_tasks(a, kinds, with_ns=True)
    elif a.command == "recreate":
        tasks = create_tasks(a, kinds, with_ns=False)
    elif a.command == "delete":
        tasks = delete_tasks(a, kinds)
    else:
        tasks = cleanup_tasks(a)
    errors = run(tasks, a.workers if a.command in ("create", "recreate") else min(a.workers, 8), f"{a.command} units {a.from_unit}-{a.to_unit}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
