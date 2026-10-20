#!/bin/bash
# Export the raw time series of a benchmark run window to CSV files (one per query) and record
# the run in runs.json, so that scripts/render-charts.py can draw the graphs from committed data.
#
# usage: scripts/export-series.sh "<run label>" <kind> <window minutes> [end unix timestamp] [results dir]
#   kind: steady | outage | compaction | churn | baseline
#   results dir default: results/$(date -u +%F)
# env: NAMESPACE (default otel-metrics-export), COLLECTOR (default otel), KUBECONFIG,
#      STEP (query step seconds, default 30), EXTRA_SERIES (series added by the load generator, informational),
#      ONLY_MISSING=1 (backfill: write only the CSV files that do not exist yet, do not touch runs.json)
#      PROFILE=collector-only: the option 2 collectors (collector-only/, namespace otel-platform-metrics by default):
#        the series are split by collector (node / cluster), the load is the idle-pod deployment, and the run
#        records VARIANT (deployment | statefulset-ta), CONFIG (free text: interval, kubelet jobs, file_storage)
#        and MARKERS ("name=unix ts;name=unix ts", e.g. the outage start and end) in runs.json
set -uo pipefail
cd "$(dirname "$0")/.."
label=$1; kind=$2; win=$3; end=${4:-$(date +%s)}; dir=${5:-results/$(date -u +%F)}
profile=${PROFILE:-remotewrite}
if [ "$profile" = collector-only ] || [ "$profile" = k8scluster ]; then ns=${NAMESPACE:-otel-platform-metrics}; else ns=${NAMESPACE:-otel-metrics-export}; fi
col=${COLLECTOR:-otel}; step=${STEP:-30}
start=$((end - win*60))
slug=$(echo "$label" | tr -c 'A-Za-z0-9\n' '-' | sed -E 's/-+/-/g; s/^-//; s/-$//' | tr 'A-Z' 'a-z')
out="$dir/raw/$slug"; mkdir -p "$out"
AUTH=$(mktemp); chmod 600 "$AUTH"
printf 'Authorization: Bearer %s\n' "$(oc create token prometheus-k8s -n openshift-monitoring --duration=30m)" > "$AUTH"
HOST=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')
CA=$(mktemp); trap 'rm -f "$CA" "$AUTH"' EXIT
oc get configmap default-ingress-cert -n openshift-config-managed -o jsonpath='{.data.ca-bundle\.crt}' > "$CA"
[ -s "$CA" ] || { echo "could not read the ingress CA bundle"; exit 1; }
pods="pod=~\"${col}-collector-.*\""; mon="job=\"${col}-collector-monitoring\""
# query list: one 'name|promql' per line (plain bash 3 compatible, no associative arrays)
if [ "$profile" = collector-only ]; then
# cAdvisor series of the collector containers and the collectors' own telemetry (PodMonitor 07-uwm-podmonitor.yaml),
# both split by collector through the pod name; plus the control plane cost of the design (API server node proxy
# requests, kube-apiserver CPU and memory) and the cluster shape (running pods, pods per node, platform Prometheus series)
cpods="pod=~\"otel-(node|cluster)-collector-.*\""; tj="job=\"${ns}/otel-collectors-telemetry\""
bycol() { echo "label_replace($1, \"collector\", \"\$1\", \"pod\", \"otel-(node|cluster)-collector-.*\")"; }
cadv_cpu="rate(container_cpu_usage_seconds_total{namespace=\"$ns\",container=\"otc-container\",$cpods}[2m])"
cadv_wss="container_memory_working_set_bytes{namespace=\"$ns\",container=\"otc-container\",$cpods}"
QUERIES=$(cat <<EOQ
collector_cpu_cores|sum by (collector) ($(bycol "$cadv_cpu"))
collector_cpu_cores_max_pod|max by (collector) ($(bycol "$cadv_cpu"))
collector_wss_bytes|sum by (collector) ($(bycol "$cadv_wss"))
collector_wss_bytes_max_pod|max by (collector) ($(bycol "$cadv_wss"))
collector_rss_bytes|max by (collector) ($(bycol "otelcol_process_memory_rss{namespace=\"$ns\",$tj,$cpods}"))
collector_rss_bytes_sum|sum by (collector) ($(bycol "otelcol_process_memory_rss{namespace=\"$ns\",$tj,$cpods}"))
receiver_accepted_points_s|sum by (collector) ($(bycol "rate(otelcol_receiver_accepted_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
receiver_accepted_points_s_by_receiver|sum by (collector, receiver) ($(bycol "rate(otelcol_receiver_accepted_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
receiver_refused_points_s|sum by (collector) ($(bycol "rate(otelcol_receiver_refused_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
exporter_sent_points_s|sum by (collector) ($(bycol "rate(otelcol_exporter_sent_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
exporter_failed_points_s|sum by (collector) ($(bycol "rate(otelcol_exporter_send_failed_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
exporter_enqueue_failed_points_s|sum by (collector) ($(bycol "rate(otelcol_exporter_enqueue_failed_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
exporter_queue_items|sum by (collector) ($(bycol "otelcol_exporter_queue_size{namespace=\"$ns\",$tj,$cpods}"))
memory_limiter_refused_points_s|sum by (collector) ($(bycol "rate(otelcol_processor_memory_limiter_refused_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
scraper_errored_points_s|sum by (collector) ($(bycol "rate(otelcol_scraper_errored_metric_points{namespace=\"$ns\",$tj,$cpods}[2m])"))
ta_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="$ns",pod=~"otel-cluster-targetallocator-.*",container!=""}[2m]))
ta_wss_bytes|sum(container_memory_working_set_bytes{namespace="$ns",pod=~"otel-cluster-targetallocator-.*",container!=""})
sink_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="$ns",pod=~"sink-collector-.*",container="otc-container"}[2m]))
sink_wss_bytes|sum(container_memory_working_set_bytes{namespace="$ns",pod=~"sink-collector-.*",container="otc-container"})
apiserver_node_proxy_req_s|sum(rate(apiserver_request_total{resource="nodes",subresource="proxy"}[2m]))
apiserver_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="openshift-kube-apiserver",container="kube-apiserver"}[2m]))
apiserver_wss_bytes|sum(container_memory_working_set_bytes{namespace="openshift-kube-apiserver",container="kube-apiserver"})
kubelet_cpu_cores|sum by (node) (rate(container_cpu_usage_seconds_total{id="/system.slice/kubelet.service"}[2m]))
cluster_pods_running|sum(kube_pod_status_phase{phase="Running"})
cluster_pods_per_node|count by (node) (kube_pod_info * on (namespace, pod) group_left() (kube_pod_status_phase{phase="Running"} == 1))
prometheus_head_series|sum by (pod) (prometheus_tsdb_head_series{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"})
option1_rw_samples_s|sum(rate(prometheus_remote_storage_samples_total{remote_name="otel-collector"}[2m]))
EOQ
)
elif [ "$profile" = k8scluster ]; then
# the k8s_cluster-only collector (08-k8scluster-collector.yaml) against kube-state-metrics on the same cluster, plus the
# API server view (list rate, watch rate, open watches and stored objects per resource) and the object inventory
kpod="pod=~\"otel-k8scluster-collector-.*\""; tj="job=\"${ns}/otel-collectors-telemetry\""
res='deployments|replicasets|pods|jobs|cronjobs|horizontalpodautoscalers|resourcequotas|clusterresourcequotas|configmaps|services|namespaces|nodes|daemonsets|statefulsets|endpoints|endpointslices'
QUERIES=$(cat <<EOQ
collector_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="$ns",container="otc-container",$kpod}[2m]))
collector_wss_bytes|sum(container_memory_working_set_bytes{namespace="$ns",container="otc-container",$kpod})
collector_rss_bytes|max(otelcol_process_memory_rss{namespace="$ns",$tj,$kpod})
receiver_accepted_points_s|sum(rate(otelcol_receiver_accepted_metric_points{namespace="$ns",$tj,$kpod}[2m]))
receiver_refused_points_s|sum(rate(otelcol_receiver_refused_metric_points{namespace="$ns",$tj,$kpod}[2m]))
exporter_queue_items|sum(otelcol_exporter_queue_size{namespace="$ns",$tj,$kpod})
memory_limiter_refused_points_s|sum(rate(otelcol_processor_memory_limiter_refused_metric_points{namespace="$ns",$tj,$kpod}[2m]))
ksm_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="openshift-monitoring",container="kube-state-metrics"}[2m]))
ksm_wss_bytes|sum(container_memory_working_set_bytes{namespace="openshift-monitoring",container="kube-state-metrics"})
ksm_rss_bytes|max(process_resident_memory_bytes{job="kube-state-metrics"})
ksm_samples_per_scrape|max(scrape_samples_scraped{job="kube-state-metrics",container="kube-rbac-proxy-main"})
ksm_watch_s|sum by (resource) (rate(kube_state_metrics_watch_total[2m]))
ksm_inventory|label_replace(count(kube_deployment_spec_replicas{namespace="otel-load-objects"}), "kind", "deployments", "", "") or label_replace(count(kube_replicaset_spec_replicas{namespace="otel-load-objects"}), "kind", "replicasets", "", "") or label_replace(count(kube_job_info{namespace="otel-load-objects"}), "kind", "jobs", "", "") or label_replace(count(kube_cronjob_info{namespace="otel-load-objects"}), "kind", "cronjobs", "", "") or label_replace(count(kube_horizontalpodautoscaler_spec_max_replicas{namespace="otel-load-objects"}), "kind", "hpas", "", "") or label_replace(count(kube_resourcequota{namespace="otel-load-objects",type="hard"}), "kind", "quotas", "", "") or label_replace(count(kube_configmap_info{namespace="otel-load-objects"}), "kind", "configmaps", "", "") or label_replace(count(kube_service_info{namespace="otel-load-objects"}), "kind", "services", "", "")
apiserver_list_s|sum by (resource) (rate(apiserver_request_total{verb="LIST",resource=~"$res"}[2m]))
apiserver_watch_s|sum by (resource) (rate(apiserver_request_total{verb="WATCH",resource=~"$res"}[2m]))
apiserver_watchers|sum by (resource) (apiserver_longrunning_requests{verb="WATCH",resource=~"$res"})
apiserver_storage_objects|max by (resource) (apiserver_storage_objects{resource=~"deployments.apps|replicasets.apps|configmaps|services|jobs.batch|cronjobs.batch|horizontalpodautoscalers.autoscaling|resourcequotas|clusterresourcequotas.quota.openshift.io|pods"})
apiserver_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="openshift-kube-apiserver",container="kube-apiserver"}[2m]))
apiserver_wss_bytes|sum(container_memory_working_set_bytes{namespace="openshift-kube-apiserver",container="kube-apiserver"})
kcm_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="openshift-kube-controller-manager",container="kube-controller-manager"}[2m]))
etcd_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="openshift-etcd",container="etcd"}[2m]))
cluster_pods_running|sum(kube_pod_status_phase{phase="Running"})
prometheus_head_series|sum by (pod) (prometheus_tsdb_head_series{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"})
option1_rw_samples_s|sum(rate(prometheus_remote_storage_samples_total{remote_name="otel-collector"}[2m]))
EOQ
)
else
QUERIES=$(cat <<EOQ
collector_cpu_cores|sum(rate(container_cpu_usage_seconds_total{namespace="$ns",container="otc-container",$pods}[2m]))
collector_wss_bytes|sum(container_memory_working_set_bytes{namespace="$ns",container="otc-container",$pods})
collector_rss_bytes|max(otelcol_process_memory_rss{namespace="$ns",$mon})
receiver_accepted_points_s|sum(rate(otelcol_receiver_accepted_metric_points{namespace="$ns",$mon}[2m]))
receiver_refused_points_s|sum(rate(otelcol_receiver_refused_metric_points{namespace="$ns",$mon}[2m]))
exporter_sent_points_s|sum(rate(otelcol_exporter_sent_metric_points{namespace="$ns",$mon}[2m]))
exporter_failed_points_s|sum(rate(otelcol_exporter_send_failed_metric_points{namespace="$ns",$mon}[2m]))
exporter_queue_items|sum(otelcol_exporter_queue_size{namespace="$ns",$mon})
rw_samples_s|sum(rate(prometheus_remote_storage_samples_total{remote_name="otel-collector"}[2m]))
rw_bytes_s|sum(rate(prometheus_remote_storage_bytes_total{remote_name="otel-collector"}[2m]))
rw_pending_samples|sum(prometheus_remote_storage_samples_pending{remote_name="otel-collector"})
rw_failed_samples_s|sum(rate(prometheus_remote_storage_samples_failed_total{remote_name="otel-collector"}[2m]))
rw_retried_samples_s|sum(rate(prometheus_remote_storage_samples_retried_total{remote_name="otel-collector"}[2m]))
rw_shards|sum(prometheus_remote_storage_shards{remote_name="otel-collector"})
rw_send_latency_p99_s|histogram_quantile(0.99, sum by (le) (rate(prometheus_remote_storage_sent_batch_duration_seconds_bucket{remote_name="otel-collector"}[2m])))
prometheus_cpu_cores|sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="openshift-monitoring",container="prometheus",pod=~"prometheus-k8s-.*"}[2m]))
prometheus_wss_bytes|sum by (pod) (container_memory_working_set_bytes{namespace="openshift-monitoring",container="prometheus",pod=~"prometheus-k8s-.*"})
prometheus_head_series|sum by (pod) (prometheus_tsdb_head_series{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"})
prometheus_head_chunks|sum by (pod) (prometheus_tsdb_head_chunks{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"})
prometheus_samples_appended_s|sum(rate(prometheus_tsdb_head_samples_appended_total{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"}[2m]))
prometheus_series_created_s|sum(rate(prometheus_tsdb_head_series_created_total{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"}[2m]))
prometheus_compactions_total|sum by (pod) (prometheus_tsdb_compactions_total{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"})
prometheus_compaction_running|max by (pod) (prometheus_tsdb_compaction_running{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*"})
uwm_samples_appended_s|sum(rate(prometheus_tsdb_head_samples_appended_total{namespace="openshift-user-workload-monitoring"}[2m]))
uwm_cpu_cores|sum by (pod) (rate(container_cpu_usage_seconds_total{namespace="openshift-user-workload-monitoring",container="prometheus",pod=~"prometheus-user-workload-.*"}[2m]))
uwm_wss_bytes|sum by (pod) (container_memory_working_set_bytes{namespace="openshift-user-workload-monitoring",container="prometheus",pod=~"prometheus-user-workload-.*"})
uwm_head_series|sum by (pod) (prometheus_tsdb_head_series{namespace="openshift-user-workload-monitoring",pod=~"prometheus-user-workload-.*"})
uwm_head_chunks|sum by (pod) (prometheus_tsdb_head_chunks{namespace="openshift-user-workload-monitoring",pod=~"prometheus-user-workload-.*"})
uwm_series_created_s|sum(rate(prometheus_tsdb_head_series_created_total{namespace="openshift-user-workload-monitoring",pod=~"prometheus-user-workload-.*"}[2m]))
uwm_compactions_total|sum by (pod) (prometheus_tsdb_compactions_total{namespace="openshift-user-workload-monitoring",pod=~"prometheus-user-workload-.*"})
EOQ
)
fi
while IFS="|" read -r name query; do
  [ -n "$name" ] || continue
  if [ -n "${ONLY_MISSING:-}" ] && [ -s "$out/$name.csv" ]; then continue; fi
  curl -s --cacert "$CA" -H @"$AUTH" "https://$HOST/api/v1/query_range" \
    --data-urlencode "query=$query" --data-urlencode "start=$start" --data-urlencode "end=$end" --data-urlencode "step=$step" \
  | python3 -c '
import json, sys, csv
d = json.load(sys.stdin)
w = csv.writer(sys.stdout); w.writerow(["ts", "series", "value"])
for s in d.get("data", {}).get("result", []):
    lab = ",".join(f"{k}={v}" for k, v in sorted(s.get("metric", {}).items())) or "all"
    for ts, v in s["values"]:
        if v not in ("NaN", "+Inf", "-Inf"): w.writerow([int(float(ts)), lab, v])
' > "$out/$name.csv" || echo "query $name failed"
done <<< "$QUERIES"
if [ -n "${ONLY_MISSING:-}" ]; then echo "backfilled missing series in $out"; exit 0; fi
# cluster shape at the end of the window
nodes=$(oc get nodes --no-headers | wc -l | tr -d ' ')
workers=$(oc get nodes -l node-role.kubernetes.io/worker --no-headers | wc -l | tr -d ' ')
pods_running=$(oc get pods -A --field-selector=status.phase=Running --no-headers | wc -l | tr -d ' ')
if [ "$profile" = collector-only ] || [ "$profile" = k8scluster ]; then
  load_pods=$(oc get deploy load-pods -n "$ns" -o jsonpath='{.status.readyReplicas}' 2>/dev/null); load_pods=${load_pods:-0}
  replicas=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.otel-cluster,app.kubernetes.io/component=opentelemetry-collector" --no-headers 2>/dev/null | wc -l | tr -d ' ')
  node_pods=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.otel-node" --no-headers 2>/dev/null | wc -l | tr -d ' ')
  restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.otel-cluster,app.kubernetes.io/component=opentelemetry-collector" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{"\n"}{end}' 2>/dev/null | awk '{s+=$1} END {print s+0}')
  node_restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.otel-node" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{"\n"}{end}' 2>/dev/null | awk '{s+=$1} END {print s+0}')
  image=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.otel-cluster,app.kubernetes.io/component=opentelemetry-collector" -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null)
  pods_per_node=$(oc get pods -A --field-selector=status.phase=Running -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort | uniq -c | awk 'BEGIN{printf "{"} {printf "%s\"%s\": %s", (NR>1?", ":""), $2, $1} END{printf "}"}')
  master_alloc=$(oc get nodes -l node-role.kubernetes.io/control-plane -o jsonpath='{range .items[*]}{.status.allocatable.cpu}{" "}{.status.allocatable.memory}{"\n"}{end}' | head -1)
  extra_json=", \"profile\": \"$profile\", \"variant\": \"${VARIANT:-deployment}\", \"config\": \"${CONFIG:-}\", \"collector_image\": \"$image\", \"node_collector_pods\": $node_pods, \"node_collector_restarts\": $node_restarts, \"markers\": $(python3 -c 'import sys,json; m=[p.split("=",1) for p in sys.argv[1].split(";") if "=" in p]; print(json.dumps([{"name": n, "ts": int(t)} for n, t in m]))' "${MARKERS:-}")"
  shape_extra=", \"master_allocatable\": \"$master_alloc\", \"pods_per_node\": $pods_per_node"
else
  load_pods=$(oc get deploy avalanche-load -n otel-metrics-load -o jsonpath='{.status.readyReplicas}' 2>/dev/null); load_pods=${load_pods:-0}
  replicas=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${col}" --no-headers 2>/dev/null | wc -l | tr -d ' ')
  restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${col}" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{"\n"}{end}' 2>/dev/null | awk '{s+=$1} END {print s+0}')
  extra_json=""; shape_extra=""
fi
alloc=$(oc get nodes -l node-role.kubernetes.io/worker -o jsonpath='{range .items[*]}{.status.allocatable.cpu}{" "}{.status.allocatable.memory}{"\n"}{end}' | head -1)
version=$(oc get clusterversion version -o jsonpath='{.status.desired.version}')
platform=$(oc get infrastructure cluster -o jsonpath='{.status.platform}')
python3 - "$dir" <<PY
import json, os, sys
f = os.path.join(sys.argv[1], "runs.json")
runs = json.load(open(f)) if os.path.exists(f) else []
runs = [r for r in runs if r["slug"] != "$slug"]
runs.append({"label": "$label", "slug": "$slug", "kind": "$kind", "start": $start, "end": $end, "step": $step,
  "collector_replicas": $replicas, "collector_restarts": $restarts, "load_pods": $load_pods, "extra_series": int("${EXTRA_SERIES:-0}"),
  "cluster": {"version": "$version", "platform": "$platform", "nodes": $nodes, "workers": $workers,
              "worker_allocatable": "$alloc", "pods_running": $pods_running$shape_extra}$extra_json})
runs.sort(key=lambda r: r["start"])
json.dump(runs, open(f, "w"), indent=1)
print(f"recorded run '{'$label'}' ({len(runs)} runs in {f})")
PY
echo "raw series in $out"
