# OpenShift platform metrics with the OpenTelemetry collector only (no monitoring stack)

Proof of concept for option 2 of TRACING-4524 (task TRACING-6910): collect the OpenShift platform metrics with the
Red Hat build of OpenTelemetry collector and operator alone, without any component of the in-cluster monitoring
stack, and export them to any backend. Nothing in `openshift-monitoring` is read, copied or modified; the stack is
only used afterwards as the measurement instrument for the sizing. Option 1 (remote write v2 from the stack) is one
level up in [`../`](../).

```
node collector (DaemonSet, one pod per node)          cluster collector (Deployment, 1 replica;
  host_metrics   root_path /hostfs (read-only)          StatefulSet + target allocator to scale)
  kubelet_stats  auth_type kubeConfig ->                k8s_cluster     distribution: openshift (TP)
                 API server node proxy                  prometheus      one kubernetes_sd job per endpoint,
  resource_detection (openshift, k8s_api) (TP)                          service account token, kube root CA
  memory_limiter, otlp_http (resilient settings)                        or service CA (openshift-service-ca.crt)
                                                        resource_detection, memory_limiter, otlp_http
                        both --OTLP--> any backend (here the vendor stand-in Prometheus, or the nop sink)
```

| File | Purpose |
|---|---|
| `00-namespace.yaml` | The `otel-platform-metrics` namespace |
| `01-rbac-scc.yaml` | Service accounts, the unprivileged `SecurityContextConstraints` of the node collector (hostPath read-only, root with `spc_t`, no privileged container, no host PID/network), the `ClusterRole`s of both collectors (kubelet through the API server proxy; `/metrics`, `/metrics/resources`, `namespace/metrics`, `routers/metrics`, `registry/metrics`, `dnses` for the platform endpoints; the `k8s_cluster` list/watch rules) |
| `02-node-collector.yaml` | `host_metrics` and `kubelet_stats` receivers, `resource_detection`, resilient `otlp_http` exporter |
| `03-cluster-collector.yaml` | **Generated** by `scripts/gen-cluster-collector.py` from `scripts/platform-endpoints.tsv`: `k8s_cluster` receiver, one `prometheus` receiver job per platform endpoint (50 jobs), the kubelet `/metrics`, `/metrics/cadvisor`, `/metrics/resource`, `/metrics/probes` jobs through the API server node proxy, the collectors' own telemetry job, the receiver debug API on `127.0.0.1:9090` (`/api/v1/targets` shows the last error of every target); the endpoints that a token cannot reach are listed as comments at the end |
| `04-cluster-collector-ta.yaml` | Generated scale-out variant: StatefulSet with 2 replicas, target allocator with `prometheusCR.enabled: false` (shards the same jobs without ServiceMonitor CRDs, own service account and `ClusterRole`), `k8s_leader_elector` for `k8s_cluster` |
| `05-sink-collector.yaml` | OTLP nop sink (contrib image) for runs where the backend must not be the bottleneck |
| `06-vendor-prometheus.yaml` | Vendor stand-in: Prometheus with the OTLP receiver, to inspect the names, types and attributes |
| `load/pause-pods.yaml` | Idle pods to scale the number of pods and containers for the sizing tiers |
| `scripts/platform-endpoints.tsv` | Catalog: namespace, service, port, path, auth kind used by the monitoring stack, TLS server name of every platform ServiceMonitor endpoint outside `openshift-monitoring` (derived from the ServiceMonitors and Services of an OpenShift 5.0 cluster) |
| `scripts/gen-cluster-collector.py` | Renders `03-cluster-collector.yaml` (`ta` argument: `04-cluster-collector-ta.yaml`) |
| `scripts/run-sizing.sh`, `scripts/collect.sh` | Sizing tiers and the per-window summary read from the vendor Prometheus (collector CPU and memory from the cAdvisor job, throughput and queue from the collectors' own telemetry) |
| `scripts/outage-test.sh` | Backend outage test: scales the vendor Prometheus to 0 for N minutes and reports queue, refused points, restarts and the samples that reached the backend |
| `results/` | Measured runs |
| `FEATURE-PARITY.md` | Component check (nothing to add to the product) and the feature parity table against the monitoring stack |

## Deploy

```bash
export KUBECONFIG=...
oc apply -f 00-namespace.yaml -f 01-rbac-scc.yaml -f 06-vendor-prometheus.yaml -f 05-sink-collector.yaml
oc apply -f 02-node-collector.yaml -f 03-cluster-collector.yaml      # or 04-cluster-collector-ta.yaml instead of 03
oc port-forward -n otel-platform-metrics svc/vendor-prometheus 9090:9090   # query system_cpu_time_seconds_total, k8s_pod_phase, apiserver_request_total, up
```

Permissions worth knowing: `nodes/proxy` get (both collectors) lets the service account read every read-only kubelet
endpoint through the API server, container logs included; it is the same rule the operator generates for the
`kubelet_stats` receiver and the price of not copying the rotating, namespaced kubelet serving CA. The cluster
collector's `/metrics` non-resource URL and the `namespace/metrics`, `routers/metrics`, `registry/metrics` and
`dnses` rules only read metrics.

With the Red Hat build of OpenTelemetry operator `spec.image` is not needed; the digest in the CRs is the product
collector 0.158 used with the upstream operator v0.161 for this PoC. To regenerate the cluster collector after editing
the catalog: `scripts/gen-cluster-collector.py > 03-cluster-collector.yaml`.

## Checks that were done

- Node collector pods on every node under the unprivileged SCC, `otelcol_scraper_errored_metric_points` = 0 for every
  `host_metrics` scraper, `kubelet_stats` through the API server node proxy with 0 refused points.
- Health of every scrape target from the receiver debug API (`oc port-forward pod/<cluster collector> 9090` and
  `curl localhost:9090/api/v1/targets`); the results are in `results/` and in the comments at the end of
  `03-cluster-collector.yaml`.
- Metric names, types and resource attributes in the vendor Prometheus.
- Target allocator sharding (TA API `/jobs/<job>/targets?collector_id=<pod>`) and the leader election lease.
- Sizing tiers with `scripts/run-sizing.sh`, backend outage with `scripts/outage-test.sh`.
