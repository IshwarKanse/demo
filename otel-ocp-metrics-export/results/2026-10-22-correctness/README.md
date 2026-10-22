# Data correctness check: Prometheus remote write v2 into the `prometheus_remote_write` receiver (2026-10-22)

Question: is the telemetry the OpenTelemetry collector emits an exact, complete copy of what
Prometheus sent, and where it is not, what exactly differs. Results in [`summary.md`](./summary.md);
per-window comparison reports in `compare-w1.md` (steady state, 12 minutes) and `compare-w2.md`
(2 minute backend outage and replay, 9 minutes); machine-readable numbers in `compare.json`.

## Senders, collectors, sink

| | Image | Role |
|---|---|---|
| platform Prometheus (production path) | the cluster's `prometheus-k8s` 3.13.2, two replicas, `remoteWrite[].messageVersion: V2.0` | sends every platform series untyped (no metadata WAL records in 3.10 to 3.15) |
| typed Prometheus | `quay.io/prometheus/prometheus:main` (digest `sha256:296477a5…`, built 2026-10-21) with `metadata-wal-records`, `exemplar-storage`, `created-timestamp-zero-ingestion`, native histogram scraping, NHCB conversion, classic histograms still scraped, `send_native_histograms` and `send_exemplars` | sends typed series with unit and help, native histograms, NHCB and exemplars |
| `prod` collector | Red Hat build of OpenTelemetry 0.158.0 (operator default image, operator from the Red Hat Operators catalog) | production path: receiver → `memory_limiter` → `otlphttp` to the sink; second pipeline `filter` (whole metric families only) → `file` |
| `prod-contrib` collector | `docker.io/otel/opentelemetry-collector-contrib:0.164.0-nightly.29f43fe` (digest `sha256:16c804bb…`, built 2026-10-21) | the same production stream into the newest upstream receiver, `file` dump only |
| `typed` collector | the same contrib nightly | typed path: receiver → `memory_limiter` → `otlphttp` to the sink, and the complete stream to `file` |
| sink | `quay.io/prometheus/prometheus:main` with `--web.enable-otlp-receiver`, `translation_strategy: NoTranslation`, `promote_all_resource_attributes`, 1 h out-of-order window, PVC | OTLP backend that keeps everything and answers PromQL |
| avalanche | `quay.io/prometheuscommunity/avalanche:v0.7.0` | 3 gauges, 3 counters, 2 classic histograms, 1 native histogram, 1 summary, 20 series each |
| exemplar-app, stale-app | hand-written OpenMetrics 1.0 exposition (`manifests/08-exemplar-app.yaml`) | counter and histogram with trace exemplars, resetting counter, NaN/±Inf gauge, escaped label value, summary, info; stale-app is scaled to 0 inside the window |

No `batch` processor anywhere; the exporter settings are the documented production ones
(unlimited retries, item-sized queue of 100,000 with `block_on_overflow`, exporter-side batching).

## Method

`scripts/run-window.sh` drives the timeline: window 1 is 12 minutes of steady state with the
stale target scaled to 0 at minute 5; window 2 (9 minutes) starts with the OTLP sink scaled to 0
for 2 minutes, then the replay. `scripts/collect.sh` then fetches, through `oc port-forward`:

- the raw samples of the senders over each window with an instant query and a range selector
  (`{...}[Ns]` at the window end returns the stored samples with their real millisecond
  timestamps, unlike `query_range`, which evaluates at steps), per platform replica directly from
  the `prometheus-k8s-N` pod (Thanos would deduplicate the replicas);
- the sender and collector counters at both window boundaries (`prometheus_remote_storage_*`,
  `prometheus_tsdb_head_samples_appended_total`, `otelcol_receiver_*`, `otelcol_exporter_*`);
- the typed sender's exemplars and metadata, and the sink's exemplars;
- sample counts per metric family over the window from every sender and from the sink
  (`scripts/family-counts.py`, one query per family: Prometheus 3 rejects `count_over_time`
  across families whose label sets collide once the name is dropped);
- the `file` exporter dumps of the three collectors (gzipped in the sidecar and streamed out).

`scripts/compare.py` maps every dumped data point back to a Prometheus series (`service.name` →
`job`, `service.instance.id` → `instance`, attributes → labels; the platform external labels
`prometheus` and `prometheus_replica` select the replica) and compares, per series, the set of
(timestamp, value) pairs with the sender's TSDB; histograms are compared on count, sum and the
per-bucket counts derived from the exponential schema or the custom bounds. Range selectors are
left-open, so a window (S, E] keeps the samples with S < t ≤ E on both sides.

## Files

- `manifests/`: everything applied to the cluster (operator subscription, namespace, sink,
  collectors, senders, apps, the `cluster-monitoring-config` with the two remote write entries).
- `scripts/`: `run-window.sh`, `collect.sh`, `family-counts.py`, `compare.py`, `scrub.py`.
- `raw/`: the collected material, with IP addresses, node names and ids replaced by `scrub.py`.
  The file exporter dumps (hundreds of MB) are not committed; `compare-w*.md` carry their
  evaluation and the examples.
- `timeline.txt`: every action of the run with its timestamp.
