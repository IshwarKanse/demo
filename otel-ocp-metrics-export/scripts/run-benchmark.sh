#!/bin/bash
# Run the load tiers and collect one results row per tier.
#
# Prerequisites: the manifests are applied (see README), KUBECONFIG points at the cluster.
# usage: scripts/run-benchmark.sh <results.md> [tier pod counts...]
#   default tiers: 0 4 10 20 (avalanche pods: +0, +100k, +250k, +500k series)
# env: SETTLE_MIN (default 4), WINDOW_MIN (default 15), COLLECTOR_IMAGE (patch spec.image of the
#      collector, needed with the upstream operator), REPLICAS (collector replicas, default 1)
set -euo pipefail
cd "$(dirname "$0")/.."
results=$1; shift
tiers=("$@"); [ ${#tiers[@]} -gt 0 ] || tiers=(0 4 10 20)
settle=${SETTLE_MIN:-4}; window=${WINDOW_MIN:-15}; replicas=${REPLICAS:-1}
ns=otel-metrics-export
if [ -n "${COLLECTOR_IMAGE:-}" ]; then
  oc patch opentelemetrycollector otel -n "$ns" --type=merge -p "{\"spec\":{\"image\":\"${COLLECTOR_IMAGE}\",\"replicas\":${replicas}}}"
else
  oc patch opentelemetrycollector otel -n "$ns" --type=merge -p "{\"spec\":{\"replicas\":${replicas}}}"
fi
oc rollout status deploy/otel-collector -n "$ns" --timeout=5m
if [ ! -s "$results" ]; then
  cat > "$results" <<EOT
| scenario | collector replicas | samples/s in | CPU cores avg / p95 | working set MiB avg / max | RSS MiB max | queue max | Prometheus pending max | failed/s max | retried/s max | restarts |
|---|---|---|---|---|---|---|---|---|---|---|
EOT
fi
for pods in "${tiers[@]}"; do
  echo "== $(date -u +%FT%TZ) tier: $pods avalanche pods (+$((pods*25000)) series), collector replicas $replicas"
  oc scale deploy/avalanche-load -n otel-metrics-load --replicas="$pods"
  if [ "$pods" -gt 0 ]; then oc rollout status deploy/avalanche-load -n otel-metrics-load --timeout=5m; fi
  echo "   settling ${settle} min, measuring ${window} min"
  sleep $(( (settle + window) * 60 ))
  NAMESPACE=$ns COLLECTOR=otel scripts/collect.sh "platform + UWM + $((pods*25000)) extra series, ${replicas} replica(s)" "$window" "$(date +%s)" "$results"
done
echo "results appended to $results"
