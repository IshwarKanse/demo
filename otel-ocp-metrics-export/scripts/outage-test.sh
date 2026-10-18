#!/bin/bash
# Simulate a backend outage: scale the OTLP sink to 0 for N minutes, restore it, and report what
# the collector and the Prometheus instances did (memory peak, restarts, refused/failed samples,
# time to drain the backlog).
# usage: scripts/outage-test.sh [outage minutes, default 5] [results.md]
set -euo pipefail
cd "$(dirname "$0")/.."
minutes=${1:-5}; results=${2:-}
ns=otel-metrics-export
restarts_before=$(oc get pods -n "$ns" -l app.kubernetes.io/instance=${ns}.otel -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}' | tr ' ' '+' | sed 's/+$//' | bc)
echo "== $(date -u +%FT%TZ) sink down for ${minutes} min"
# the sink is managed by the operator, so its replicas are set on the OpenTelemetryCollector CR
# (scaling the Deployment directly is reverted by the operator within seconds)
oc patch opentelemetrycollector sink -n "$ns" --type=merge -p '{"spec":{"replicas":0}}'
until [ "$(oc get pods -n "$ns" -l app.kubernetes.io/instance=${ns}.sink --no-headers 2>/dev/null | wc -l | tr -d ' ')" = "0" ]; do sleep 5; done
echo "   sink pods are gone"
sleep $((minutes*60))
echo "== $(date -u +%FT%TZ) sink up"
oc patch opentelemetrycollector sink -n "$ns" --type=merge -p '{"spec":{"replicas":1}}'
oc rollout status deploy/sink-collector -n "$ns" --timeout=5m
drain_start=$(date +%s)
for i in $(seq 1 60); do
  pending=$(scripts/pq.sh 'sum(prometheus_remote_storage_samples_pending{remote_name="otel-collector"})' | awk -F'=> ' '{print int($2)}')
  if [ "${pending:-0}" -lt 30000 ]; then break; fi
  sleep 10
done
drain=$(( $(date +%s) - drain_start ))
restarts_after=$(oc get pods -n "$ns" -l app.kubernetes.io/instance=${ns}.otel -o jsonpath='{range .items[*]}{.status.containerStatuses[0].restartCount}{" "}{end}' | tr ' ' '+' | sed 's/+$//' | bc)
win=$((minutes + 8))
NAMESPACE=$ns COLLECTOR=otel scripts/collect.sh "outage ${minutes} min + recovery" "$win" "$(date +%s)" "$results"
echo "collector restarts during the outage: $((restarts_after - restarts_before)); backlog drained ${drain}s after the sink came back (pending samples < 30k)"
