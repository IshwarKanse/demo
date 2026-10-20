#!/usr/bin/env python3
"""Generate 03-cluster-collector.yaml: the OpenTelemetryCollector CR with the k8s_cluster receiver and one
prometheus receiver scrape job per platform endpoint listed in scripts/platform-endpoints.tsv
(namespace, service, port name, metrics path, auth kind used by the monitoring stack, TLS server name).

The jobs follow the three patterns of the documentation: kube-apiserver through the `kubernetes`
endpoint in `default` (kube root CA, server_name kubernetes), kube-scheduler / kube-controller-manager
(service CA, server_name <svc>.<ns>.svc), and kube-rbac-proxy protected endpoints (same). All use the
collector service account token. The optional kubelet jobs go through the API server node proxy.

usage: scripts/gen-cluster-collector.py > 03-cluster-collector.yaml
       scripts/gen-cluster-collector.py ta > 04-cluster-collector-ta.yaml   (scale-out variant)
       BACKEND=sink scripts/gen-cluster-collector.py > 03-cluster-collector-sizing.yaml   (sizing: nop sink as backend)

The `ta` variant is the scale-out shape: a StatefulSet with two replicas, the target allocator with
prometheusCR.enabled: false (it shards the same kubernetes_sd scrape jobs across the replicas without any
ServiceMonitor CRD) and the k8s_leader_elector extension so that only one replica runs the k8s_cluster
receiver. The target allocator needs its own service account and ClusterRole for the discovery.
"""
import csv, sys, os
TA = len(sys.argv) > 1 and sys.argv[1] == "ta"
# BACKEND=sink sends the platform metrics to the nop sink collector (sizing runs: the vendor stand-in Prometheus
# cannot ingest 450,000 series fast enough and would throttle the collector through the exporter queue); the
# collectors' own telemetry then goes to the vendor Prometheus through a second pipeline, where collect.sh reads it.
SINK = os.environ.get("BACKEND", "vendor") == "sink"
# FILE_STORAGE=1 persists the exporter queue on disk with the file_storage extension (an emptyDir here; a PVC in
# production so that the queue survives a pod reschedule, not only a container restart)
FILE_STORAGE = os.environ.get("FILE_STORAGE", "") == "1"
# INTERVAL overrides the 30 s scrape and collection interval (sizing: sample rate tiers at a fixed series count)
INTERVAL = os.environ.get("INTERVAL", "30s")
# KUBELET_JOBS=0 leaves out the optional kubelet jobs through the API server node proxy (/metrics, /metrics/cadvisor,
# /metrics/resource, /metrics/probes): the documented shape is the k8s_cluster receiver plus the platform endpoints,
# the kubelet_stats receiver of the node collector already covers the pods and containers
KUBELET_JOBS = os.environ.get("KUBELET_JOBS", "1") == "1"

HERE = os.path.dirname(os.path.abspath(__file__))
TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"
SA_CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
SVC_CA = "/etc/service-ca/service-ca.crt"
# IMAGE="" leaves spec.image out so that the Red Hat build of OpenTelemetry operator uses its default collector image
IMAGE = os.environ.get("IMAGE", "registry.redhat.io/rhosdt/opentelemetry-collector-rhel9@sha256:359726016f0f6b9a408cc47f03be66b095f8b4e725f482442f1a02c0ce8b9128")

# the drop lists the Cluster Monitoring Operator applies to the heaviest control plane endpoints
APISERVER_DROPS = [
    r"etcd_(debugging|disk|server).*",
    r"apiserver_admission_controller_admission_latencies_seconds_.*",
    r"apiserver_admission_step_admission_latencies_seconds_.*",
    r"scheduler_(e2e_scheduling_latency_microseconds|scheduling_algorithm_predicate_evaluation|scheduling_algorithm_priority_evaluation|scheduling_algorithm_preemption_evaluation|scheduling_algorithm_latency_microseconds|binding_latency_microseconds|scheduling_latency_seconds)",
    r"apiserver_(request_count|request_latencies|request_latencies_summary|dropped_requests|storage_data_key_generation_latencies_microseconds|storage_transformation_failures_total|storage_transformation_latencies_microseconds|proxy_tunnel_sync_latency_secs)",
    r"reflector_(items_per_list|items_per_watch|list_duration_seconds|lists_total|short_watches_total|watch_duration_seconds|watches_total)",
    r"etcd_(helper_cache_hit_count|helper_cache_miss_count|helper_cache_entry_count|request_cache_get_latencies_summary|request_cache_add_latencies_summary|request_latencies_summary)",
    r"transformation_(transformation_latencies_microseconds|failures_total)",
    r"network_plugin_operations_latency_microseconds|sync_proxy_rules_latency_microseconds|rest_client_request_latency_seconds",
    r"apiserver_request_slo_duration_seconds_.*",
    # the stack keeps only a subset of the request duration histogram buckets
    ("__name__, le", r"apiserver_request_duration_seconds_bucket;(0.4|0.6|0.8|1.25|1.5|3|6|8|15)(\.0)?"),
]
KCM_DROPS = [
    r"etcd_(debugging|disk|request|server).*",
    r"rest_client_request_latency_seconds_(bucket|count|sum)",
    r"root_ca_cert_publisher_sync_duration_seconds_(bucket|count|sum)",
]

def q(s):
    return "'" + s.replace("'", "''") + "'"

def job(name, ns, svc, port, path, ca, server_name, drops=(), pod_labels=True):
    out = [f"            - job_name: {q(name)}",
           "              scheme: https",
           "              authorization:",
           f"                credentials_file: {TOKEN}",
           "              tls_config:",
           f"                ca_file: {ca}",
           f"                server_name: {server_name}"]
    if path != "/metrics":
        out.append(f"              metrics_path: {path}")
    out += ["              kubernetes_sd_configs:",
            "                - role: endpoints",
            "                  namespaces:",
            f"                    names: [{ns}]",
            "              relabel_configs:",
            "                - source_labels: [__meta_kubernetes_service_name, __meta_kubernetes_endpoint_port_name]",
            f"                  regex: {svc};{port}",
            "                  action: keep"]
    if pod_labels:
        out += ["                - source_labels: [__meta_kubernetes_namespace]",
                "                  target_label: namespace",
                "                - source_labels: [__meta_kubernetes_pod_name]",
                "                  target_label: pod",
                "                - source_labels: [__meta_kubernetes_pod_node_name]",
                "                  target_label: node"]
    if drops:
        out.append("              metric_relabel_configs:")
        for d in drops:
            labels, regex = (d if isinstance(d, tuple) else ("__name__", d))
            out += [f"                - source_labels: [{labels}]",
                    f"                  regex: {q(regex)}",
                    "                  action: drop"]
    return "\n".join(out)

# endpoints that cannot be scraped with a service account token (verified on OpenShift 5.0); they are
# listed at the end of the generated manifest and in the documentation as not covered
SKIP = {
    ("openshift-apiserver", "check-endpoints"): "serving certificate valid for localhost only; the monitoring stack uses insecureSkipVerify",
    ("openshift-network-diagnostics", "network-check-source"): "on OpenShift 4.22 a self-signed localhost certificate (check-endpoints-signer, 1 s validity); on 5.0 a service CA certificate",
    ("openshift-cluster-csi-drivers", "aws-ebs-csi-driver-controller-metrics"): "kube-rbac-proxy without SubjectAccessReview permission, accepts only the monitoring stack client certificate",
    ("openshift-marketplace", "marketplace-operator-metrics"): "client certificate required (tls: certificate required)",
    ("openshift-cluster-node-tuning-operator", "node-tuning-operator"): "HTTP 401 with a token, client certificate only",
    ("openshift-cluster-samples-operator", "metrics"): "HTTP 401 with a token, client certificate only",
    ("openshift-dns", "dns-default"): "NetworkPolicy dns-default admits port 9154 only from the namespace openshift-monitoring",
    ("openshift-dns-operator", "metrics"): "NetworkPolicy dns-operator-allow admits port 9393 only from the namespace openshift-monitoring",
    ("openshift-ingress-operator", "metrics"): "NetworkPolicy ingress-operator-allow admits port 9393 only from the namespace openshift-monitoring",
}
jobs = []
skipped = []
# pattern 1: kube-apiserver through the kubernetes endpoint in default (no pods behind it)
jobs.append(job("kube-apiserver", "default", "kubernetes", "https", "/metrics", SA_CA, "kubernetes", APISERVER_DROPS, pod_labels=False))
# patterns 2 and 3: every endpoint the monitoring stack scrapes with a token or a client certificate (token verified)
rows = list(csv.reader(open(os.path.join(HERE, "platform-endpoints.tsv")), delimiter="\t"))
multi = {}
for ns, svc, port, path, auth, server_name in rows:
    if path == "/metrics":
        multi[(ns, svc)] = multi.get((ns, svc), 0) + 1
if True:
    for ns, svc, port, path, auth, server_name in rows:
        if not server_name:
            server_name = f"{svc}.{ns}.svc"
        # job name: the namespace without the openshift- prefix, the service when it adds information,
        # the port when the service exposes several metrics ports
        short = ns.removeprefix("openshift-")
        name = short if svc in ("metrics", short, "scheduler", "api", "cco-metrics") else f"{short}/{svc}"
        if multi.get((ns, svc), 0) > 1:
            name = f"{name}/{port}"
        if path == "/metrics/resources":
            name = f"{short}/resources"
        if ns == "openshift-kube-apiserver":
            continue  # scraped through default/kubernetes above
        if (ns, svc) in SKIP:
            skipped.append(f"#   {ns}/{svc} ({port}): {SKIP[(ns, svc)]}")
            continue
        drops = KCM_DROPS if svc == "kube-controller-manager" else ()
        jobs.append(job(name, ns, svc, port, path, SVC_CA, server_name, drops))
# kubelet endpoints through the API server node proxy (optional; the kubelet_stats receiver of the node
# collector covers the same data with OpenTelemetry names)
for name, path in (("kubelet", "/metrics"), ("kubelet-cadvisor", "/metrics/cadvisor"), ("kubelet-resource", "/metrics/resource"), ("kubelet-probes", "/metrics/probes")) if KUBELET_JOBS else ():
    jobs.append("\n".join([
        f"            - job_name: {q(name)}",
        "              scheme: https",
        "              authorization:",
        f"                credentials_file: {TOKEN}",
        "              tls_config:",
        f"                ca_file: {SA_CA}",
        "              kubernetes_sd_configs:",
        "                - role: node",
        "              relabel_configs:",
        "                - target_label: __address__",
        "                  replacement: kubernetes.default.svc:443",
        "                - source_labels: [__meta_kubernetes_node_name]",
        "                  regex: (.+)",
        "                  target_label: __metrics_path__",
        # $$ keeps the $ from the collector's environment variable expansion
        f"                  replacement: /api/v1/nodes/$${{1}}/proxy{path}",
        "                - source_labels: [__meta_kubernetes_node_name]",
        "                  target_label: node",
    ]))

ta_rbac = """---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: otel-cluster-ta
  namespace: otel-platform-metrics
---
# Target allocator: service discovery only (the collector service account does the scraping)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-platform-metrics-ta
rules:
- apiGroups: [""]
  resources: ["nodes", "nodes/metrics", "services", "endpoints", "pods", "namespaces"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get"]
- apiGroups: ["discovery.k8s.io"]
  resources: ["endpointslices"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch"]
- nonResourceURLs: ["/metrics"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-platform-metrics-ta
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: otel-platform-metrics-ta
subjects:
- kind: ServiceAccount
  name: otel-cluster-ta
  namespace: otel-platform-metrics
---
# Leader election lease for the k8s_cluster receiver
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: otel-cluster-leader-election
  namespace: otel-platform-metrics
rules:
- apiGroups: ["coordination.k8s.io"]
  resources: ["leases"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: otel-cluster-leader-election
  namespace: otel-platform-metrics
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: otel-cluster-leader-election
subjects:
- kind: ServiceAccount
  name: otel-cluster
  namespace: otel-platform-metrics
""" if TA else ""
mode_block = """  mode: statefulset
  replicas: 2
  targetAllocator:
    enabled: true
    serviceAccount: otel-cluster-ta
    allocationStrategy: consistent-hashing
    filterStrategy: relabel-config
    prometheusCR:
      enabled: false""" if TA else """  mode: deployment
  replicas: 1"""
ext_items = ""
if TA:
    ext_items += """      k8s_leader_elector:
        auth_type: serviceAccount
        lease_name: otel-cluster-k8s-cluster-receiver
        lease_namespace: otel-platform-metrics
"""
if FILE_STORAGE:
    ext_items += """      file_storage:
        directory: /var/lib/otelcol/file_storage
        create_directory: true
"""
extensions_block = ("    extensions:\n" + ext_items) if ext_items else ""
ext_names = [n for n, on in (("k8s_leader_elector", TA), ("file_storage", FILE_STORAGE)) if on]
queue_storage = "\n          storage: file_storage" if FILE_STORAGE else ""
fs_volume_mount = """
  - name: file-storage
    mountPath: /var/lib/otelcol/file_storage""" if FILE_STORAGE else ""
fs_volume = """
  - name: file-storage
    emptyDir: {}""" if FILE_STORAGE else ""
leader_field = "\n        k8s_leader_elector: k8s_leader_elector" if TA else ""
service_extensions = (f"      extensions: [{', '.join(ext_names)}]\n") if ext_names else ""
header = ("# Cluster collector, scale-out variant: a StatefulSet with two replicas. The target allocator shards the\n"
          "# kubernetes_sd scrape jobs of the prometheus receiver across the replicas (prometheusCR.enabled: false,\n"
          "# no ServiceMonitor or PodMonitor CRD involved) and the k8s_leader_elector extension lets only one\n"
          "# replica run the k8s_cluster receiver, so nothing is collected twice.") if TA else \
         ("# Cluster collector: one Deployment replica")
# the collectors' own telemetry (port 8888 of every collector pod in the namespace), so that the sizing can be
# read from the backend without the monitoring stack
telemetry_job = "\n".join([
    "            - job_name: 'otel-collectors'",
    "              kubernetes_sd_configs:",
    "                - role: pod",
    "                  namespaces:",
    "                    own_namespace: true",
    "              relabel_configs:",
    "                - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_component, __meta_kubernetes_pod_container_port_number]",
    "                  regex: opentelemetry-collector;8888",
    "                  action: keep",
    "                - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_instance]",
    "                  regex: .*\\.(.*)",
    "                  target_label: collector",
    "                - source_labels: [__meta_kubernetes_pod_name]",
    "                  target_label: pod",
    "                - source_labels: [__meta_kubernetes_pod_node_name]",
    "                  target_label: node",
])
if not SINK:
    jobs.append(telemetry_job)
sink_receivers = f"""
      prometheus/telemetry:
        config:
          global:
            scrape_interval: 30s
          scrape_configs:
{telemetry_job}""" if SINK else ""
sink_exporter = """
      otlp_http/telemetry:
        endpoint: http://vendor-prometheus.otel-platform-metrics.svc.cluster.local:9090/api/v1/otlp
        tls:
          insecure: true""" if SINK else ""
sink_pipeline = """
        metrics/telemetry:
          receivers: [prometheus/telemetry]
          processors: [memory_limiter]
          exporters: [otlp_http/telemetry]""" if SINK else ""
main_endpoint = "http://sink-collector.otel-platform-metrics.svc.cluster.local:4318" if SINK else "http://vendor-prometheus.otel-platform-metrics.svc.cluster.local:9090/api/v1/otlp"

image_line = f"  image: {IMAGE}\n" if IMAGE else ""
print(f"""{header} with the k8s_cluster receiver (cluster object state, with the k8s_cluster receiver (cluster object state,
# distribution: openshift, Technology Preview) and the prometheus receiver scraping the control plane
# and operator /metrics endpoints with the collector service account token. The kube-apiserver is
# verified with the kube root CA (server_name kubernetes); every other endpoint serves a service CA
# certificate and is verified with the openshift-service-ca.crt config map that exists in every
# namespace. One scrape job per endpoint because the service CA certificates carry only the
# <service>.<namespace>.svc name and tls_config.server_name is a per-job setting. The kubelet jobs
# at the end go through the API server node proxy.
#
# GENERATED by scripts/gen-cluster-collector.py from scripts/platform-endpoints.tsv; edit those.{ta_rbac}
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-cluster-service-ca
  namespace: otel-platform-metrics
  annotations:
    service.beta.openshift.io/inject-cabundle: "true"
---
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: otel-cluster
  namespace: otel-platform-metrics
spec:
{image_line}{mode_block}
  serviceAccount: otel-cluster
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: "2"
      memory: 4Gi
  volumeMounts:
  - name: service-ca
    mountPath: /etc/service-ca
    readOnly: true{fs_volume_mount}
  volumes:
  - name: service-ca
    configMap:
      name: otel-cluster-service-ca{fs_volume}
  config:
{extensions_block}    receivers:
      k8s_cluster:{leader_field}
        distribution: openshift
        collection_interval: {INTERVAL}
        node_conditions_to_report: [Ready, MemoryPressure, DiskPressure, PIDPressure]
        allocatable_types_to_report: [cpu, memory, pods]
      prometheus:
        # the agent-mode API of the receiver (/api/v1/targets with the last scrape error of every
        # target) for troubleshooting; not exposed outside the pod
        api_server:
          enabled: true
          server_config:
            endpoint: 127.0.0.1:9090
        config:
          global:
            scrape_interval: {INTERVAL}
            scrape_timeout: 10s
          scrape_configs:
{chr(10).join(jobs)}{sink_receivers}
    processors:
      memory_limiter:
        check_interval: 1s
        limit_percentage: 80
        spike_limit_percentage: 20
      resource_detection:
        detectors: [openshift]
        override: false
        timeout: 5s
    exporters:
      otlp_http:
        # the third-party backend; here the vendor stand-in Prometheus with the OTLP receiver (or the nop sink)
        endpoint: {main_endpoint}
        tls:
          insecure: true
        retry_on_failure:
          enabled: true
          max_elapsed_time: 0
        # the queue must hold the largest single scrape: the cAdvisor endpoint of a node with 300 pods or the
        # kube-apiserver exceed 50,000 data points, and a request larger than the queue is rejected outright
        # ("element size too large")
        sending_queue:
          enabled: true
          sizer: items
          queue_size: 200000
          block_on_overflow: true{queue_storage}
          batch:
            flush_timeout: 5s
            min_size: 2000
            max_size: 8000{sink_exporter}
    service:
{service_extensions}      telemetry:
        metrics:
          readers:
          - pull:
              exporter:
                prometheus:
                  host: 0.0.0.0
                  port: 8888
      pipelines:
        metrics:
          receivers: [k8s_cluster, prometheus]
          processors: [memory_limiter, resource_detection]
          exporters: [otlp_http]{sink_pipeline}
# Platform endpoints that the monitoring stack scrapes but that a service account token cannot reach:
{chr(10).join(sorted(set(skipped)))}""")
