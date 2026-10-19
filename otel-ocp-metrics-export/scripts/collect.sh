#!/bin/bash
# Summarise the collector and the Prometheus remote write metrics over a time window with
# range queries against Thanos Querier, and append one row to a markdown results table.
#
# usage: scripts/collect.sh "<scenario label>" <window minutes> [end unix timestamp] [results file]
# env:   NAMESPACE (default otel-metrics-export), COLLECTOR (default otel), KUBECONFIG
set -uo pipefail
label=$1; win=${2:-15}; end=${3:-$(date +%s)}; results=${4:-}
ns=${NAMESPACE:-otel-metrics-export}; col=${COLLECTOR:-otel}
start=$((end - win*60)); step=30
# Thanos Querier access: a token that expires with the run, read by curl from a private header file
# (never on the command line), and the cluster's ingress CA to verify the route certificate (no -k).
AUTH=$(mktemp); chmod 600 "$AUTH"
printf 'Authorization: Bearer %s\n' "$(oc create token prometheus-k8s -n openshift-monitoring --duration=30m)" > "$AUTH"
HOST=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')
CA=$(mktemp)
trap 'rm -f "$CA" "$AUTH"' EXIT
oc get configmap default-ingress-cert -n openshift-config-managed -o jsonpath='{.data.ca-bundle\.crt}' > "$CA"
[ -s "$CA" ] || { echo "could not read the ingress CA bundle (openshift-config-managed/default-ingress-cert)"; exit 1; }
q() { curl -s --cacert "$CA" -H @"$AUTH" "https://$HOST/api/v1/query_range" --data-urlencode "query=$1" --data-urlencode "start=$start" --data-urlencode "end=$end" --data-urlencode "step=$step"; }
# prints "avg p95 max" of a range query, scaled
stat() {
  python3 -c '
import json,sys
d=json.loads(sys.argv[1]); scale=float(sys.argv[2])
vals=[float(v[1])*scale for s in d.get("data",{}).get("result",[]) for v in s["values"] if v[1] not in ("NaN","+Inf","-Inf")]
if not vals: print("- - -"); sys.exit()
vals.sort(); n=len(vals)
print(f"{sum(vals)/n:.2f} {vals[int(0.95*(n-1))]:.2f} {vals[-1]:.2f}")
' "$(q "$1")" "${2:-1}"
}
pods="pod=~\"${col}-collector-.*\""
mon="job=\"${col}-collector-monitoring\""
read -r cpu_avg cpu_p95 cpu_max <<<"$(stat "sum(rate(container_cpu_usage_seconds_total{namespace=\"$ns\",container=\"otc-container\",$pods}[2m]))")"
read -r wss_avg wss_p95 wss_max <<<"$(stat "sum(container_memory_working_set_bytes{namespace=\"$ns\",container=\"otc-container\",$pods})" 0.00000095367431640625)"
read -r rss_avg rss_p95 rss_max <<<"$(stat "max(otelcol_process_memory_rss{namespace=\"$ns\",$mon})" 0.00000095367431640625)"
read -r in_avg in_p95 in_max <<<"$(stat "sum(rate(otelcol_receiver_accepted_metric_points{namespace=\"$ns\",$mon}[2m]))")"
read -r ref_avg ref_p95 ref_max <<<"$(stat "sum(rate(otelcol_receiver_refused_metric_points{namespace=\"$ns\",$mon}[2m]))")"
read -r out_avg out_p95 out_max <<<"$(stat "sum(rate(otelcol_exporter_sent_metric_points{namespace=\"$ns\",$mon}[2m]))")"
read -r fail_avg fail_p95 fail_max <<<"$(stat "sum(rate(otelcol_exporter_send_failed_metric_points{namespace=\"$ns\",$mon}[2m]))")"
read -r q_avg q_p95 q_max <<<"$(stat "sum(otelcol_exporter_queue_size{namespace=\"$ns\",$mon})")"
read -r rw_avg rw_p95 rw_max <<<"$(stat "sum(rate(prometheus_remote_storage_samples_total{remote_name=\"otel-collector\"}[2m]))")"
read -r bytes_avg bytes_p95 bytes_max <<<"$(stat "sum(rate(prometheus_remote_storage_bytes_total{remote_name=\"otel-collector\"}[2m]))" 0.001)"
read -r pend_avg pend_p95 pend_max <<<"$(stat "sum(prometheus_remote_storage_samples_pending{remote_name=\"otel-collector\"})")"
read -r rwfail_avg rwfail_p95 rwfail_max <<<"$(stat "sum(rate(prometheus_remote_storage_samples_failed_total{remote_name=\"otel-collector\"}[2m]))")"
read -r retry_avg retry_p95 retry_max <<<"$(stat "sum(rate(prometheus_remote_storage_samples_retried_total{remote_name=\"otel-collector\"}[2m]))")"
read -r lat_avg lat_p95 lat_max <<<"$(stat "histogram_quantile(0.99, sum by (le) (rate(prometheus_remote_storage_sent_batch_duration_seconds_bucket{remote_name=\"otel-collector\"}[2m])))")"
read -r pcpu_avg pcpu_p95 pcpu_max <<<"$(stat "sum(rate(container_cpu_usage_seconds_total{namespace=\"openshift-monitoring\",container=\"prometheus\",pod=~\"prometheus-k8s-.*\"}[2m]))")"
read -r pwss_avg pwss_p95 pwss_max <<<"$(stat "sum(container_memory_working_set_bytes{namespace=\"openshift-monitoring\",container=\"prometheus\",pod=~\"prometheus-k8s-.*\"})" 0.00000095367431640625)"
restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${col}" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}' 2>/dev/null | tr ' ' '+' | sed 's/+$//' | bc 2>/dev/null || echo "?")
replicas=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${col}" --no-headers 2>/dev/null | wc -l | tr -d ' ')
endiso=$(date -u -r "$end" +%FT%TZ 2>/dev/null || date -u -d "@$end" +%FT%TZ)
cat <<EOT
### $label
window: ${win} min ending $endiso, collector replicas: $replicas, container restarts: $restarts
| metric | avg | p95 | max |
|---|---|---|---|
| collector CPU (cores, all pods) | $cpu_avg | $cpu_p95 | $cpu_max |
| collector working set (MiB, all pods) | $wss_avg | $wss_p95 | $wss_max |
| collector RSS (MiB, max per pod) | $rss_avg | $rss_p95 | $rss_max |
| receiver accepted points/s | $in_avg | $in_p95 | $in_max |
| receiver refused points/s | $ref_avg | $ref_p95 | $ref_max |
| exporter sent points/s | $out_avg | $out_p95 | $out_max |
| exporter send failed points/s | $fail_avg | $fail_p95 | $fail_max |
| exporter queue size (items) | $q_avg | $q_p95 | $q_max |
| Prometheus remote write samples/s (all instances) | $rw_avg | $rw_p95 | $rw_max |
| Prometheus remote write KB/s (compressed) | $bytes_avg | $bytes_p95 | $bytes_max |
| Prometheus pending samples | $pend_avg | $pend_p95 | $pend_max |
| Prometheus failed samples/s | $rwfail_avg | $rwfail_p95 | $rwfail_max |
| Prometheus retried samples/s | $retry_avg | $retry_p95 | $retry_max |
| Prometheus send latency p99 (s) | $lat_avg | $lat_p95 | $lat_max |
| platform Prometheus CPU (cores, all replicas) | $pcpu_avg | $pcpu_p95 | $pcpu_max |
| platform Prometheus working set (MiB, all replicas) | $pwss_avg | $pwss_p95 | $pwss_max |

EOT
if [ -n "$results" ]; then
  printf '| %s | %s | %s | %s / %s | %s / %s | %s | %s | %s | %s | %s | %s |\n' \
    "$label" "$replicas" "$in_avg" "$cpu_avg" "$cpu_p95" "$wss_avg" "$wss_max" "$rss_max" "$q_max" "$pend_max" "$rwfail_max" "$retry_max" "$restarts" >> "$results"
fi
