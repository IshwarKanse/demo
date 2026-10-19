# Proof of concept: OpenShift monitoring metrics to the OpenTelemetry Collector via remote write v2

The resource files used for the proof of concept on OpenShift 5.0 (TRACING-6909), kept here so
that the team can reproduce it. The findings, the data fidelity table, the resilience tests and the
first benchmark are in the design document linked from the Jira epic TRACING-4524; the reusable
sizing benchmark that followed is one level up in [`../`](../).

Everything runs in the `observability` namespace; the backend stand-in is an in-cluster Prometheus
with the OTLP receiver, so no third-party account or credential is needed.

| File | Purpose |
|---|---|
| `00-namespace.yaml` | The `observability` namespace |
| `01-vendor-prometheus.yaml` | Prometheus 3.13 with `--web.enable-otlp-receiver` as the stand-in for a third-party OTLP backend (`promote_all_resource_attributes` so every attribute is visible as a label) |
| `02-otel-collector.yaml` | The collector under test: `prometheus_remote_write` receiver, `memory_limiter`, `otlphttp` exporter with the resilient settings (unlimited retries, item-sized bounded queue with `block_on_overflow`, exporter-side batching), contrib 0.161.0 image because the upstream operator's default image lacks the receiver |
| `03-cluster-monitoring-config.yaml` | `enableUserWorkload: true` and remote write v2 (`messageVersion: V2.0`) from the platform Prometheus; merge it into an existing config map |
| `04-user-workload-monitoring-config.yaml` | Remote write v2 from the user workload Prometheus |
| `05-sample-app.yaml` | `avalanche` sample application with every Prometheus metric type (gauge, counter, classic histogram, native histogram, summary) and its `ServiceMonitor`, in `prw-demo` |
| `06-debug-collector.yaml` | Second collector with the debug exporter at detailed verbosity to see how the metric types arrive (today: every series as an untyped gauge, see the design document and MON-4412); add its URL as a second `remoteWrite` entry in `04-user-workload-monitoring-config.yaml` |
| `07-product-collector-validation.yaml` | The Red Hat build of OpenTelemetry 3.11 collector image (0.158.0) with the same recommended configuration, used to prove that the shipped product parses it and exports over OTLP |
| `benchmark/avalanche-load.yaml` | Load generator used for the first benchmark (25,000 gauge series per pod, scaled to 1, 4 and 10 pods) |

## How the PoC was run

```bash
oc apply -f 00-namespace.yaml -f 01-vendor-prometheus.yaml -f 02-otel-collector.yaml -f 05-sample-app.yaml
oc apply -f 03-cluster-monitoring-config.yaml -f 04-user-workload-monitoring-config.yaml   # merge, do not overwrite
oc get prometheus k8s -n openshift-monitoring -o jsonpath='{.spec.remoteWrite}'           # shows messageVersion: V2.0
oc port-forward -n observability svc/vendor-prometheus 9090:9090                          # query up, node_cpu_seconds_total, avalanche_*
```

Checks that were done against this setup:

- Remote write health on both Prometheus instances through Thanos Querier: `prometheus_remote_storage_samples_total` (throughput), `_samples_failed_total` (must stay 0), `_samples_pending`, `_samples_retried_total`, `_sent_batch_duration_seconds` p99.
- Metric types with `06-debug-collector.yaml` on the UWM stream.
- Backend outage: `oc scale deploy/vendor-prometheus -n observability --replicas=0` for 5 minutes, then back to 1; compare `count_over_time(<series>[15m])` in the vendor Prometheus with the expected sample count, and check collector restarts (`oc get pods -n observability`) and `otelcol_exporter_send_failed_metric_points`.
- Default exporter settings versus the resilient settings in `02-otel-collector.yaml` (the defaults OOM-killed the collector during the outage and dropped data).
- First benchmark with `benchmark/avalanche-load.yaml` at 1, 4 and 10 pods and with 2 collector replicas; the production-grade run with the product image is in [`../results/`](../results/).
