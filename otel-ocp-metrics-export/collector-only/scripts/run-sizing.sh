#!/bin/bash
# Sizing run: measure both collectors at rest and with extra idle pods on the cluster.
# usage: scripts/run-sizing.sh <results file> [pod tiers...]   (default tiers: 0 300 600)
# env:   NAMESPACE (default otel-platform-metrics), SETTLE_MIN (default 4), WINDOW_MIN (default 15), KUBECONFIG
# Every tier scales the load-pods Deployment, waits for the pods to be ready, settles, then summarises a
# steady-state window with scripts/collect.sh. The load is scaled back to 0 at the end.
set -uo pipefail
results=$1; shift
tiers=${*:-0 300 600}
ns=${NAMESPACE:-otel-platform-metrics}; settle=${SETTLE_MIN:-4}; win=${WINDOW_MIN:-15}
here=$(cd "$(dirname "$0")" && pwd)
# the platform metrics go to the nop sink during the run; the collectors' own telemetry goes to the vendor Prometheus
BACKEND=sink "$here/gen-cluster-collector.py" | oc apply -f - >/dev/null
sed 's#http://vendor-prometheus.otel-platform-metrics.svc.cluster.local:9090/api/v1/otlp#http://sink-collector.otel-platform-metrics.svc.cluster.local:4318#' "$here/../02-node-collector.yaml" | oc apply -f - >/dev/null
oc rollout status deploy/otel-cluster-collector -n "$ns" --timeout=180s >/dev/null; oc rollout status ds/otel-node-collector -n "$ns" --timeout=180s >/dev/null
echo "$(date -u +%FT%TZ) collectors export to the nop sink"
for n in $tiers; do
  echo "$(date -u +%FT%TZ) tier: $n extra pods"
  oc scale deploy/load-pods -n "$ns" --replicas="$n" >/dev/null
  for i in $(seq 1 60); do ready=$(oc get deploy load-pods -n "$ns" -o jsonpath='{.status.readyReplicas}'); [ "${ready:-0}" -ge "$n" ] && break; sleep 10; done
  echo "$(date -u +%FT%TZ) load pods ready: ${ready:-0}; settling ${settle} min, window ${win} min"
  sleep $(( (settle + win) * 60 ))
  NAMESPACE=$ns "$here/collect.sh" "platform metrics + $n idle pods" "$win" "$(date +%s)" "$results"
done
oc scale deploy/load-pods -n "$ns" --replicas=0 >/dev/null
# back to the vendor Prometheus as backend
oc apply -f "$here/../03-cluster-collector.yaml" -f "$here/../02-node-collector.yaml" >/dev/null
echo "$(date -u +%FT%TZ) done"
