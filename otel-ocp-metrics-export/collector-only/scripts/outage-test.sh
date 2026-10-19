#!/bin/bash
# Backend outage test: with the collectors in the sizing configuration (platform metrics to the nop sink, own
# telemetry to the vendor Prometheus), scale the sink to 0 for N minutes, scale it back, and report from the
# telemetry what happened: exporter queue, points refused by the receivers (scrapes dropped because the queue was
# full for longer than the scrape timeout), points the exporter failed, restarts, and the recovery. Pull receivers
# have no upstream WAL: the scrapes that happen while the queue is full are the data that is lost.
#
# usage: scripts/outage-test.sh <outage minutes> [results file]
# env:   NAMESPACE (default otel-platform-metrics), KUBECONFIG, FILE_STORAGE=1 (persist the cluster collector queue on disk)
set -uo pipefail
mins=${1:-5}; results=${2:-}
ns=${NAMESPACE:-otel-platform-metrics}
here=$(cd "$(dirname "$0")" && pwd)
BACKEND=sink "$here/gen-cluster-collector.py" | oc apply -f - >/dev/null
sed 's#http://vendor-prometheus.otel-platform-metrics.svc.cluster.local:9090/api/v1/otlp#http://sink-collector.otel-platform-metrics.svc.cluster.local:4318#' "$here/../02-node-collector.yaml" | oc apply -f - >/dev/null
oc rollout status deploy/otel-cluster-collector -n "$ns" --timeout=180s >/dev/null; oc rollout status ds/otel-node-collector -n "$ns" --timeout=180s >/dev/null
sleep 180
start=$(date +%s)
echo "$(date -u +%FT%TZ) scaling the sink to 0 for $mins min"
# the sink is operator-managed: scale it through the OpenTelemetryCollector CR (the operator reverts a direct Deployment scale within seconds)
oc patch otelcol sink -n "$ns" --type merge -p '{"spec":{"replicas":0}}' >/dev/null
for i in $(seq 1 30); do [ "$(oc get deploy sink-collector -n "$ns" -o jsonpath='{.status.readyReplicas}')" = "" ] && break; sleep 2; done
echo "$(date -u +%FT%TZ) sink pods: $(oc get pods -n "$ns" -l app.kubernetes.io/instance=${ns}.sink --no-headers 2>/dev/null | wc -l | tr -d ' ')"
sleep $((mins * 60))
echo "$(date -u +%FT%TZ) scaling the sink back to 1"
oc patch otelcol sink -n "$ns" --type merge -p '{"spec":{"replicas":1}}' >/dev/null
oc rollout status deploy/sink-collector -n "$ns" --timeout=180s >/dev/null
back=$(date +%s)
sleep 300
end=$(date +%s)
oc port-forward -n "$ns" svc/vendor-prometheus 19090:9090 >/dev/null 2>&1 & PF=$!
trap 'kill $PF 2>/dev/null' EXIT
curl -s --retry 10 --retry-connrefused --retry-delay 1 -o /dev/null http://localhost:19090/-/ready
qi() { curl -s "http://localhost:19090/api/v1/query" --data-urlencode "query=$1" --data-urlencode "time=$2" | jq -r '.data.result[0].value[1] // empty | tonumber | floor'; }
win=$((end - start))
row() { # collector
  local c=$1
  local qmax refused failed accepted sent restarts drain
  qmax=$(qi "max(max_over_time(otelcol_exporter_queue_size{collector=\"$c\"}[${win}s]))" "$end")
  refused=$(qi "sum(increase(otelcol_receiver_refused_metric_points_total{collector=\"$c\"}[${win}s]))" "$end")
  failed=$(qi "sum(increase(otelcol_exporter_send_failed_metric_points_total{collector=\"$c\"}[${win}s]))" "$end")
  accepted=$(qi "sum(increase(otelcol_receiver_accepted_metric_points_total{collector=\"$c\"}[${win}s]))" "$end")
  sent=$(qi "sum(increase(otelcol_exporter_sent_metric_points_total{collector=\"$c\"}[${win}s]))" "$end")
  rss=$(qi "max(max_over_time(otelcol_process_memory_rss{collector=\"$c\"}[${win}s])) / 1048576" "$end")
  restarts=$(oc get pods -n "$ns" -l "app.kubernetes.io/instance=${ns}.${c}" -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}' | tr ' ' '\n' | awk '{s+=$1} END {print s+0}')
  # when did the queue return to (near) 0 after the sink came back
  drain=$(curl -s "http://localhost:19090/api/v1/query_range" --data-urlencode "query=sum(otelcol_exporter_queue_size{collector=\"$c\"})" --data-urlencode "start=$back" --data-urlencode "end=$end" --data-urlencode "step=30" | jq -r --argjson b "$back" '[.data.result[0].values[] | select((.[1]|tonumber) < 100)][0][0] // empty | . - $b' )
  echo "| $c | $restarts | ${qmax:--} | ${refused:--} | ${failed:--} | ${accepted:--} | ${sent:--} | ${rss:--} | ${drain:--} |"
}
out=$(cat <<EOT
### Backend outage of $mins min${FILE_STORAGE:+, file_storage queue} (sink scaled to 0 from $(date -u -r "$start" +%FT%TZ 2>/dev/null || date -u -d "@$start" +%FT%TZ), window incl. 5 min recovery)
| collector | restarts | max queue (items) | receiver refused points | exporter failed points | receiver accepted points | exporter sent points | max RSS MiB | queue drained after (s) |
|---|---|---|---|---|---|---|---|---|
$(row otel-node)
$(row otel-cluster)
EOT
)
echo "$out"
[ -n "$results" ] && printf '\n%s\n' "$out" >> "$results"
# back to the vendor Prometheus as backend
oc apply -f "$here/../03-cluster-collector.yaml" -f "$here/../02-node-collector.yaml" >/dev/null
echo "$(date -u +%FT%TZ) collectors export to the vendor Prometheus again"
