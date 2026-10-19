# Feature parity: OpenShift monitoring stack vs. collector-only collection (option 2)

Verified on OpenShift 5.0.0-0.nightly-2026-10-16 with the Red Hat build of OpenTelemetry collector 0.158.0
(`redhat-opentelemetry-collector`, branch `rhosdt-0.158`, identical to `rhosdt-3.11`). "Component" names the
product component that provides the feature; "GA"/"TP" is the support level in the product documentation.

## Product components needed

No additional upstream component has to be added to the Red Hat build of OpenTelemetry for option 2. Every
component used is in the 0.158 manifest:

| Component | Role in option 2 | Support level |
|---|---|---|
| `host_metrics` receiver (`hostmetricsreceiver`) | node CPU, memory, load, filesystem, disk, network, paging, process counts (replaces node-exporter) | GA |
| `kubelet_stats` receiver (`kubeletstatsreceiver`) | node, pod, container and volume usage from the kubelet (replaces the kubelet/cAdvisor scrape) | GA |
| `prometheus` receiver (`prometheusreceiver`) | control plane, operator and kubelet `/metrics` endpoints, service discovery, relabeling (replaces the Prometheus scrape) | GA |
| `k8s_cluster` receiver (`k8sclusterreceiver`) | pod phase, restarts, deployment/daemonset/statefulset/job counts, node conditions and allocatable, quotas (replaces kube-state-metrics) | TP |
| `resource_detection` processor (`resourcedetectionprocessor`) | `cloud.*`, `k8s.cluster.name`, `k8s.node.name` resource attributes | TP |
| `memory_limiter` processor | bounded memory, back pressure | GA |
| `filter`, `transform`, `attributes`, `resource` processors | dropping or renaming series (relabeling the Prometheus way is in the receiver) | GA |
| `otlp`, `otlp_http`, `awsemf`, `googlecloud`, `prometheus`, `prometheusremotewrite` exporters | the backend | GA / TP per exporter |
| `k8s_leader_elector` extension | one active `k8s_cluster` receiver with several replicas | TP |
| `file_storage` extension | persistent exporter queue during a backend outage | GA |
| Target allocator (operator) | sharding the scrape jobs across replicas without ServiceMonitor CRDs | GA |

Components that exist upstream but are not in the product and are **not needed**: `metricstransform` processor
(`transform` covers renaming), `deltatocumulative` (not relevant for scraped data). Components that would be needed
for parity but do not exist in OpenTelemetry at all: a recording rule or alerting engine, a query API, a
dashboard, a `metrics.k8s.io` server.

## Feature parity table

| Monitoring stack feature | Stack component | Option 2 | Collector component | Status |
|---|---|---|---|---|
| Node CPU, memory, load, filesystem, disk, network, paging | node-exporter | `system.cpu.time`, `system.memory.usage`, `system.cpu.load_average.*`, `system.filesystem.*`, `system.disk.*`, `system.network.*`, `system.paging.*`, `system.processes.*` on every node (DaemonSet) | `host_metrics` | Covered (OpenTelemetry names, mapping table in the docs) |
| Node-exporter extras: pressure stall (PSI), netstat/sockstat, conntrack, hardware (NVMe, multipath, EDAC), textfile metrics of the machine-config daemon, `node_uname_info`, `node_os_info`, time/NTP | node-exporter collectors | not available (`system.network.conntrack.*` is optional in `host_metrics`; MCD metrics come from its own endpoint) | - | Gap |
| Kubelet, pod, container and volume usage | kubelet `/metrics/cadvisor`, `/metrics`, `/metrics/probes`, `/metrics/resource` | `k8s.node.*`, `k8s.pod.*`, `container.*`, `k8s.volume.*` through the API server node proxy, or the original cAdvisor/kubelet names through the prometheus receiver node-proxy jobs | `kubelet_stats`, `prometheus` | Covered |
| Pod phase, container restarts and readiness, deployment/replicaset/daemonset/statefulset/job/cronjob counts, HPA, resource quotas, cluster resource quotas, node conditions and allocatable | kube-state-metrics, openshift-state-metrics (quotas) | `k8s.pod.phase`, `k8s.container.restarts`, `k8s.container.ready`, `k8s.deployment.*`, `k8s.daemonset.*`, `k8s.statefulset.*`, `k8s.job.*`, `k8s.hpa.*`, `k8s.resource_quota.*`, `openshift.clusterquota.*`, `k8s.node.condition_*`, `k8s.node.allocatable_*` | `k8s_cluster` | Covered, Technology Preview; one metric per condition, no `kube_*` names |
| kube-state-metrics labels and annotations metrics (`kube_pod_labels`, `kube_node_labels`, `kube_*_annotations`), `kube_pod_info`, `kube_node_info`, owner references, PV/PVC phase, service and endpoint objects, certificate signing requests | kube-state-metrics | partly: pod and node metadata are resource attributes of the kubelet and cluster receiver series; PV/PVC phase and capacity are optional `k8s_cluster` metrics; services and endpoints are optional (`k8s.service.*`); no labels/annotations export | `k8s_cluster`, `k8s_attributes` | Partial |
| OpenShift objects: routes, builds, deployment configs, groups, cluster resource quotas | openshift-state-metrics | `openshift.clusterquota.*` and `openshift.appliedclusterquota.*` only; `openshift_route_*`, builds, deployment configs, groups are not collected (the `k8s_objects` receiver can watch any object as logs, not as metrics) | `k8s_cluster` | Gap except quotas |
| kube-apiserver, kube-scheduler, kube-controller-manager, openshift-apiserver, oauth, controller managers | Prometheus scrape with the metrics client certificate | the same Prometheus names, scraped with the collector service account token (`/metrics`, `/metrics/resources`) | `prometheus` | Covered (not on hosted control planes, where these run outside the cluster) |
| Operator `/metrics` endpoints behind kube-rbac-proxy or library-go secure serving (46 endpoints on this cluster) | Prometheus + ServiceMonitors | 42 of 46 scraped with the token (`/metrics`, `namespace/metrics`, `routers/metrics`, `registry/metrics`, `dnses`); one job per endpoint because `tls_config.server_name` is per job | `prometheus` | Covered with a per-endpoint job; see gaps below |
| Endpoints that accept only the monitoring stack's client certificate: cluster-version-operator, node-tuning-operator, cluster-samples-operator, marketplace-operator, CSI driver controller kube-rbac-proxy, openshift-apiserver check-endpoints (certificate for localhost) | metrics client certificate from `openshift-monitoring` | not collected | - | Gap (platform side: token authentication not offered) |
| Endpoints behind a NetworkPolicy that admits only the `openshift-monitoring` namespace: dns-default (CoreDNS), dns-operator, ingress-operator | NetworkPolicy | not collected (connection refused by policy from any other namespace) | - | Gap (platform side) |
| etcd server metrics | etcd client certificate `etcd-metric-client` | not collected (client certificate only; `etcd_request_duration_seconds` and `apiserver_storage_*` from the kube-apiserver remain) | - | Gap by design |
| User-defined project metrics (ServiceMonitor / PodMonitor of applications) | user workload monitoring, Prometheus Operator CRDs | applications are scraped with `prometheus` receiver jobs (or the target allocator with the Prometheus CRDs when the Prometheus Operator CRDs exist) | `prometheus`, target allocator | Covered by configuration, not by CRD |
| Recording rules (`namespace:container_cpu_usage_seconds_total:sum_rate`, `cluster:*`, `instance:*`) | Prometheus rules | none; aggregation belongs to the backend | - | Gap |
| Alerting rules and Alertmanager (47 PrometheusRule objects, platform alerts, routing, silences) | Prometheus, Alertmanager | none; alerting belongs to the backend | - | Gap |
| Console Observe > Metrics, Dashboards, Alerting pages; `oc adm top`; HPA on CPU/memory | Thanos Querier, metrics-server (`metrics.k8s.io`) | none; without the stack `metrics.k8s.io` is not served (`oc adm top` and HPA on resource metrics stop working) | - | Gap |
| Telemetry to Red Hat (Telemeter), Insights health data | telemeter-client | none; Insights is independent of the stack | - | Gap |
| Long-term storage, query API (PromQL), federation | Prometheus, Thanos Querier | none in the cluster; the backend provides storage and query | exporters | Different by design |
| Typed metrics: counters, histograms, summaries | Prometheus scrape | the prometheus receiver keeps the types (sums, histograms, summaries) and the kubelet and cluster receivers emit typed OpenTelemetry metrics, unlike the remote write v2 path today (MON-4412) | all receivers | Better than option 1 |
| Resource attributes `cloud.provider`, `cloud.platform`, `cloud.region`, `k8s.cluster.name` | `cluster_id` external label (Telemeter) | added to every series | `resource_detection` (TP) | Covered |
| High availability | 2 Prometheus replicas (every sample twice) | node collectors are one per node; the cluster collector scales with the target allocator (sharding, every target once) and leader election; no duplicate samples | target allocator, `k8s_leader_elector` | Covered |
| Durable buffer during a backend outage | Prometheus WAL (2h) + remote write retries | bounded exporter queue in memory or on disk (`file_storage`); scrapes that happen while the queue is full are skipped | `memory_limiter`, `file_storage` | Different: size the queue for the outage |
