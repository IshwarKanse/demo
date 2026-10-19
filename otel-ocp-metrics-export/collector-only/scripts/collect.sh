#!/bin/bash
# Summarise the resource usage and throughput of the two collectors over a time window from the collectors'
# own telemetry (process CPU and RSS, receiver, exporter and memory_limiter counters), which the cluster
# collector scrapes from every collector pod and sends to the vendor stand-in Prometheus, and append one markdown row set to a results file. Nothing from the
# OpenShift monitoring stack is used. The collectors' own counters arrive with the _total suffix and carry the
# collector label set by the otel-collectors scrape job (their job label is the collector's own service.name).
#
# usage: scripts/collect.sh "<scenario label>" <window minutes> [end unix timestamp] [results file]
# env:   NAMESPACE (default otel-platform-metrics), KUBECONFIG
set -uo pipefail
label=$1; win=${2:-15}; end=${3:-$(date +%s)}; results=${4:-}
ns=${NAMESPACE:-otel-platform-metrics}
start=$((end - win*60)); step=30
oc port-forward -n "$ns" svc/vendor-prometheus 19090:9090 >/dev/null 2>&1 & PF=$!
trap 'kill $PF 2>/dev/null' EXIT
curl -s --retry 10 --retry-connrefused --retry-delay 1 -o /dev/null http://localhost:19090/-/ready
q() { curl -s "http://localhost:19090/api/v1/query_range" --data-urlencode "query=$1" --data-urlencode "start=$start" --data-urlencode "end=$end" --data-urlencode "step=$step"; }
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
MiB=0.00000095367431640625
row() { # name, collector regex
  local c=$2
  read -r cpu_avg cpu_p95 cpu_max <<<"$(stat "sum(rate(otelcol_process_cpu_seconds_total{collector=\"$c\"}[2m]))")"
  read -r cpu1_avg cpu1_p95 cpu1_max <<<"$(stat "max(rate(otelcol_process_cpu_seconds_total{collector=\"$c\"}[2m]))")"
  read -r wss_avg wss_p95 wss_max <<<"$(stat "max(otelcol_process_memory_rss{collector=\"$c\"})" $MiB)"
  read -r in_avg in_p95 in_max <<<"$(stat "sum(rate(otelcol_receiver_accepted_metric_points_total{collector=\"$c\"}[2m]))")"
  read -r ref_avg ref_p95 ref_max <<<"$(stat "sum(rate(otelcol_receiver_refused_metric_points_total{collector=\"$c\"}[2m]))")"
  read -r fail_avg fail_p95 fail_max <<<"$(stat "sum(rate(otelcol_exporter_send_failed_metric_points_total{collector=\"$c\"}[2m]))")"
  read -r q_avg q_p95 q_max <<<"$(stat "sum(otelcol_exporter_queue_size{collector=\"$c\"})")"
  read -r ml_avg ml_p95 ml_max <<<"$(stat "sum(rate(otelcol_processor_memory_limiter_refused_metric_points_total{collector=\"$c\"}[2m]))")"
  restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${c}" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}' | tr ' ' '\n' | awk '{s+=$1} END {print s+0}')
  pods=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${c}" --no-headers | wc -l | tr -d ' ')
  cat <<EOT
| $1 ($pods pods, $restarts restarts) | CPU all pods (cores) | $cpu_avg | $cpu_p95 | $cpu_max |
| | CPU busiest pod (cores) | $cpu1_avg | $cpu1_p95 | $cpu1_max |
| | RSS busiest pod (MiB) | $wss_avg | $wss_p95 | $wss_max |
| | receiver accepted points/s | $in_avg | $in_p95 | $in_max |
| | receiver refused points/s | $ref_avg | $ref_p95 | $ref_max |
| | exporter failed points/s | $fail_avg | $fail_p95 | $fail_max |
| | exporter queue size (items) | $q_avg | $q_p95 | $q_max |
| | memory_limiter refused points/s | $ml_avg | $ml_p95 | $ml_max |
EOT
}
pods_total=$(oc get pods -A --no-headers | wc -l | tr -d ' ')
nodes=$(oc get nodes --no-headers | wc -l | tr -d ' ')
endiso=$(date -u -r "$end" +%FT%TZ 2>/dev/null || date -u -d "@$end" +%FT%TZ)
out=$(cat <<EOT
### $label
window: ${win} min ending $endiso, nodes: $nodes, pods in the cluster: $pods_total
| collector | metric | avg | p95 | max |
|---|---|---|---|---|
$(row "node collector (DaemonSet)" otel-node)
$(row "cluster collector" otel-cluster)
EOT
)
echo "$out"
[ -n "$results" ] && printf '\n%s\n' "$out" >> "$results"
