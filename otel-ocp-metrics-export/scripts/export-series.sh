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
set -uo pipefail
cd "$(dirname "$0")/.."
label=$1; kind=$2; win=$3; end=${4:-$(date +%s)}; dir=${5:-results/$(date -u +%F)}
ns=${NAMESPACE:-otel-metrics-export}; col=${COLLECTOR:-otel}; step=${STEP:-30}
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
load_pods=$(oc get deploy avalanche-load -n otel-metrics-load -o jsonpath='{.status.readyReplicas}' 2>/dev/null); load_pods=${load_pods:-0}
replicas=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${col}" --no-headers 2>/dev/null | wc -l | tr -d ' ')
restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${col}" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{"\n"}{end}' 2>/dev/null | awk '{s+=$1} END {print s+0}')
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
              "worker_allocatable": "$alloc", "pods_running": $pods_running}})
runs.sort(key=lambda r: r["start"])
json.dump(runs, open(f, "w"), indent=1)
print(f"recorded run '{'$label'}' ({len(runs)} runs in {f})")
PY
echo "raw series in $out"
