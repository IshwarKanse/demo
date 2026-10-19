# Exporting OpenShift monitoring metrics through the OpenTelemetry Collector: sizing benchmark

Manifests and scripts used to size the OpenTelemetry Collector that receives the OpenShift
in-cluster (platform) and user workload monitoring (UWM) metrics with **Prometheus remote write v2**
and exports them to an OTLP backend. The results back the resource recommendation in the
Red Hat build of OpenTelemetry documentation (TRACING-4524, TRACING-6909).

```
prometheus-k8s (2 replicas)            ─┐
                                        ├─ remote write v2 ──▶ otel-collector ──▶ OTLP ──▶ sink-collector (nop)
prometheus-user-workload (2 replicas)  ─┘    messageVersion: V2.0    prometheus_remote_write receiver
                                                                      memory_limiter, otlp_http exporter
avalanche-load (N pods x 25,000 series) ──▶ scraped by UWM
```

The resource files of the preceding proof of concept (vendor stand-in Prometheus, debug collector for the metric types, product image validation) are in [`poc/`](./poc/).

Nothing in this directory contains credentials: the backend is an in-cluster OTLP sink and the
scripts use the `oc` login of the current `KUBECONFIG`.

## Prerequisites

- OpenShift 5.0 or later (the Cluster Monitoring Operator accepts `remoteWrite[].messageVersion` since 5.0)
- Red Hat build of OpenTelemetry operator (the product collector image contains the `prometheus_remote_write` receiver), or the upstream operator with a contrib collector image (set `COLLECTOR_IMAGE`)
- `oc`, `jq`, `curl`, `python3`

## Deploy

```bash
oc apply -f manifests/00-namespace.yaml -f manifests/01-sink-collector.yaml -f manifests/02-otel-collector.yaml -f manifests/05-load-generator.yaml
# merge into an existing cluster-monitoring-config instead of overwriting it
oc apply -f manifests/03-cluster-monitoring-config.yaml -f manifests/04-user-workload-monitoring-config.yaml
```

The collector CR carries the configuration recommended in the product documentation: no `batch`
processor, `memory_limiter`, and an OTLP exporter with unlimited retries, an item-sized bounded
`sending_queue` that blocks the receiver when full and exporter-side batching, so that a backend
outage never makes the collector drop data or run out of memory (the Prometheus instances keep
the samples in their write-ahead log and retry).

## Run

```bash
export KUBECONFIG=...
# load tiers: 0, 4, 10 and 20 avalanche pods (+0, +100k, +250k, +500k series), 4 min settle + 15 min window each
scripts/run-benchmark.sh results/<date>.md 0 4 10 20
# the largest tier with two collector replicas
REPLICAS=2 scripts/run-benchmark.sh results/<date>.md 20
# 5 minute backend outage with the current load
scripts/outage-test.sh 5 results/<date>.md
```

`scripts/collect.sh` summarises one window (average, p95, max) from Thanos Querier range queries:
collector CPU and memory (kubelet), the collector's own receiver/exporter/queue metrics (scraped by
UWM through `observability.metrics.enableMetrics`), and the remote write metrics of the Prometheus
instances (throughput, pending, failed, retried, send latency). `scripts/pq.sh` runs an instant query.

The load generator adds 25,000 gauge series per pod, scraped every 30 s by UWM and forwarded by
both UWM replicas, i.e. about 1,700 samples/s per pod on top of the platform metrics.

## Results

See [`results/`](./results/) for the measured runs.

### 2026-10-18, OpenShift 5.0 on AWS, Red Hat build of OpenTelemetry collector 0.158.0

Collector: requests 500m / 512Mi, limits 2 CPU / 2Gi, one replica unless noted. Full rows in
[`results/2026-10-18-ocp-5.0-aws-product-0.158.md`](./results/2026-10-18-ocp-5.0-aws-product-0.158.md),
per-window details in [`results/2026-10-18-ocp-5.0-aws-product-0.158-details.md`](./results/2026-10-18-ocp-5.0-aws-product-0.158-details.md).

| Load | Samples/s into the collector | CPU cores (avg / p95) | Working set MiB (avg / max) | Prometheus failed / retried |
|---|---|---|---|---|
| platform + UWM (about 350k series per platform replica) | 31,600 | 0.27 / 0.29 | 88 / 108 | 0 / 0 |
| + 100,000 UWM series | 38,400 | 0.34 / 0.35 | 109 / 146 | 0 / 0 |
| + 250,000 UWM series | 48,500 | 0.42 / 0.46 | 112 / 162 | 0 / 0 |
| + 500,000 UWM series | 65,400 | 0.60 / 0.63 | 120 / 164 | 0 / 0 |
| + 500,000 UWM series, 2 replicas | 65,400 (31k + 33k) | 0.62 / 0.66 (both pods) | 199 / 222 (both pods) | 0 / 0 |
| 5 min backend outage at 47,000 samples/s + recovery | 47,100 | 0.56 / 1.94 (at the 2-core limit while catching up) | 547 / 1,971 | 0 failed, up to 70,000/s retried, 0 restarts, backlog drained 203 s after the backend came back |

CPU grows linearly with the throughput: about **1 core per 100,000 samples/s** in steady state.
Memory does not depend on the throughput in steady state (under 170 MiB working set up to 65,000
samples/s); it is driven by the exporter queue during a backend outage (100,000 queued data points
held the working set at about 360 MiB) and by the recovery burst afterwards, when the Prometheus
instances resend their backlog at more than 100,000 samples/s and the `memory_limiter` keeps the
collector under its limit by refusing requests (which Prometheus retries). No sample was lost in any
scenario, including the outage.

### Recommendation

Per collector replica, with the configuration in `manifests/02-otel-collector.yaml`:

| | Request | Limit | Why |
|---|---|---|---|
| CPU | samples/s ÷ 100,000 cores, at least 500m | 2 cores | steady state needs about 1 core per 100k samples/s; the limit is used only while catching up after a backend outage (a 5 minute backlog drained in 3.5 minutes at 2 cores) |
| Memory | 512 MiB | 2 GiB | steady state stays under 250 MiB; the 100,000-item queue adds about 250 MiB during an outage and the recovery burst needs the headroom; the `memory_limiter` (80 %) turns a shortage into back pressure instead of an OOM kill |

One replica handled 65,000 samples/s (a cluster of about 1.3 million active series across the
platform and user workload Prometheus instances, both replicas sending) with these settings.
Beyond that, or for high availability, add replicas: the collector service spreads the Prometheus
remote write shards evenly and the cost per sample does not change. With a 1 GiB memory limit,
reduce `sending_queue.queue_size` to 50000.

