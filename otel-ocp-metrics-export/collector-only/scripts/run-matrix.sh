#!/bin/bash
# Run the collector-only sizing matrix on a cluster and export every run for ../../scripts/render-charts.py
# (PROFILE=collector-only of ../../scripts/export-series.sh: raw CSV series from the Thanos Querier, runs.json).
#
# usage: scripts/run-matrix.sh <results dir> <phase> [args]
#   tiers <pods...>   idle-pod tiers with the Deployment cluster collector (default 0 300 600 850 1200)
#   ta                scale-out variant at the current tier: StatefulSet with 2 replicas + target allocator
#   nokubelet         the documented shape at the current tier: without the optional kubelet proxy jobs
#   long [min]        one long steady window at the current tier (default 150 min, 60 s step)
#   outage [fs]       5 minute sink outage at the current tier, with the file_storage queue when "fs" is given
#   rate <intervals>  scrape interval tiers at the current pod count (default 60s 15s), then back to 30s
#   restore           idle pods to 0, both collectors back to the vendor Prometheus backend
# The collectors run in the sizing shape: platform metrics to the nop sink (05-sink-collector.yaml), own telemetry
# to the vendor Prometheus (for collect.sh) and to the user workload monitoring PodMonitor (07-uwm-podmonitor.yaml,
# read by export-series.sh); spec.image left out so that the operator's default collector image is used.
# prerequisites: 00, 01, 05, 06, 07 and load/pause-pods.yaml applied, KUBECONFIG set, the operator installed.
# env: SETTLE_MIN (5), WINDOW_MIN (20), NAMESPACE (otel-platform-metrics)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../.." && pwd)
cd "$here/.."
dir=$1; phase=$2; shift 2
ns=${NAMESPACE:-otel-platform-metrics}; settle=${SETTLE_MIN:-5}; window=${WINDOW_MIN:-20}
mkdir -p "$dir"; dir=$(cd "$dir" && pwd); table="$dir/table.md"
log() { echo "== $(date -u +%FT%TZ) $*"; }
INTERVAL=${INTERVAL:-30s}; KUBELET_JOBS=${KUBELET_JOBS:-1}; FILE_STORAGE=${FILE_STORAGE:-}; VARIANT=deployment
config() {
  local jobs; jobs=$(IMAGE= BACKEND=sink INTERVAL=$INTERVAL KUBELET_JOBS=$KUBELET_JOBS "$here/gen-cluster-collector.py" | grep -c job_name)
  echo "$INTERVAL interval, $((jobs - 1)) scrape jobs $([ "$KUBELET_JOBS" = 1 ] && echo with || echo without) kubelet proxy jobs${FILE_STORAGE:+, file_storage queue}, operator default image"
}
apply_cluster() {  # [ta]
  # the operator webhook refuses a mode change on an existing CR: delete it first when switching between the
  # Deployment and the StatefulSet shape (the collector is stateless, the queue is lost either way)
  local want=deployment; [ "${1:-}" = ta ] && want=statefulset
  local cur; cur=$(oc get otelcol otel-cluster -n "$ns" -o jsonpath='{.spec.mode}' 2>/dev/null)
  if [ -n "$cur" ] && [ "$cur" != "$want" ]; then
    log "mode change $cur -> $want: deleting the otel-cluster CR first"
    oc delete otelcol otel-cluster -n "$ns" --wait=true >/dev/null
    for i in $(seq 1 60); do [ "$(oc get pods -n "$ns" -l app.kubernetes.io/instance=$ns.otel-cluster --no-headers 2>/dev/null | wc -l | tr -d ' ')" = 0 ] && break; sleep 5; done
  fi
  IMAGE= BACKEND=sink INTERVAL=$INTERVAL KUBELET_JOBS=$KUBELET_JOBS FILE_STORAGE=$FILE_STORAGE "$here/gen-cluster-collector.py" ${1:-} | oc apply -f - >/dev/null
  if [ "${1:-}" = ta ]; then
    VARIANT=statefulset-ta
    for i in $(seq 1 60); do oc get deploy otel-cluster-collector -n "$ns" >/dev/null 2>&1 || break; sleep 5; done
    oc get deploy otel-cluster-collector -n "$ns" >/dev/null 2>&1 && log "WARNING: the Deployment is still there after the mode switch"
    oc rollout status sts/otel-cluster-collector -n "$ns" --timeout=5m >/dev/null
    oc rollout status deploy/otel-cluster-targetallocator -n "$ns" --timeout=5m >/dev/null
  else
    VARIANT=deployment
    for i in $(seq 1 60); do oc get sts otel-cluster-collector -n "$ns" >/dev/null 2>&1 || break; sleep 5; done
    oc get sts otel-cluster-collector -n "$ns" >/dev/null 2>&1 && log "WARNING: the StatefulSet is still there after the mode switch"
    oc rollout status deploy/otel-cluster-collector -n "$ns" --timeout=5m >/dev/null
  fi
  log "cluster collector: $VARIANT, $(config); pods: $(oc get pods -n "$ns" -l app.kubernetes.io/instance=$ns.otel-cluster --no-headers | wc -l | tr -d ' ')"
}
apply_node() {
  sed -e 's#http://vendor-prometheus.otel-platform-metrics.svc.cluster.local:9090/api/v1/otlp#http://sink-collector.otel-platform-metrics.svc.cluster.local:4318#' \
      -e '/^  image: registry.redhat.io/d' -e "s/collection_interval: 30s/collection_interval: $INTERVAL/" 02-node-collector.yaml | oc apply -f - >/dev/null
  oc rollout status ds/otel-node-collector -n "$ns" --timeout=5m >/dev/null
  log "node collector: $INTERVAL interval; pods: $(oc get pods -n "$ns" -l app.kubernetes.io/instance=$ns.otel-node --no-headers | wc -l | tr -d ' ')"
}
set_load() {
  oc scale deploy/load-pods -n "$ns" --replicas="$1" >/dev/null
  for i in $(seq 1 90); do ready=$(oc get deploy load-pods -n "$ns" -o jsonpath='{.status.readyReplicas}'); [ "${ready:-0}" -ge "$1" ] && break; sleep 10; done
  # scaling down: wait until the pods are gone
  for i in $(seq 1 90); do [ "$(oc get pods -n "$ns" -l app=load-pods --no-headers 2>/dev/null | wc -l | tr -d ' ')" -le "$1" ] && break; sleep 10; done
  log "idle pods: $1 requested, ${ready:-0} ready, $(oc get pods -A --field-selector=status.phase=Running --no-headers | wc -l | tr -d ' ') pods running in the cluster"
}
measure() {  # label kind window_min [step] [markers] [end]
  local end=${6:-$(date +%s)}
  "$here/collect.sh" "$1" "$3" "$end" "$table" >/dev/null 2>&1 || log "collect.sh failed for $1"
  PROFILE=collector-only VARIANT=$VARIANT CONFIG="$(config)" STEP=${4:-30} MARKERS="${5:-}" "$root/scripts/export-series.sh" "$1" "$2" "$3" "$end" "$dir"
}
settle_and_measure() {  # label kind
  log "settling ${settle} min, measuring ${window} min: $1"
  sleep $(( (settle + window) * 60 ))
  measure "$1" "$2" "$window"
}
current_pods() { oc get deploy load-pods -n "$ns" -o jsonpath='{.spec.replicas}'; }
log "phase $phase $*"
case $phase in
  tiers)
    apply_cluster; apply_node
    for pods in ${*:-0 300 600 850 1200}; do
      set_load "$pods"
      settle_and_measure "tiers: $pods idle pods, deployment" steady
    done ;;
  ta)
    apply_cluster ta
    settle_and_measure "scale-out: $(current_pods) idle pods, statefulset with 2 replicas and target allocator" steady
    apply_cluster ;;
  nokubelet)
    KUBELET_JOBS=0 apply_cluster; apply_node
    KUBELET_JOBS=0 settle_and_measure "documented shape: $(current_pods) idle pods, without kubelet proxy jobs" steady
    apply_cluster ;;
  long)
    mins=${1:-150}
    log "settling ${settle} min, measuring ${mins} min: long window"
    sleep $(( (settle + mins) * 60 ))
    measure "long: $(current_pods) idle pods, ${mins} min" long "$mins" 60 ;;
  outage)
    om=5; fs=${1:-}
    if [ "$fs" = fs ]; then FILE_STORAGE=1; fi
    FILE_STORAGE=$FILE_STORAGE apply_cluster
    sleep 180
    down=$(date +%s)
    # the sink is operator-managed: scale it through the CR (the operator reverts a direct Deployment scale)
    oc patch otelcol sink -n "$ns" --type merge -p '{"spec":{"replicas":0}}' >/dev/null
    log "sink scaled to 0 for ${om} min"
    sleep $((om * 60))
    oc patch otelcol sink -n "$ns" --type merge -p '{"spec":{"replicas":1}}' >/dev/null
    oc rollout status deploy/sink-collector -n "$ns" --timeout=3m >/dev/null
    up=$(date +%s); log "sink back"
    sleep 420
    end=$(date +%s)
    FILE_STORAGE=$FILE_STORAGE measure "outage: ${om} min sink outage, $(current_pods) idle pods${FILE_STORAGE:+, file_storage queue}" outage $(( (end - down + 180) / 60 )) 15 "sink down=$down;sink up=$up" "$end"
    FILE_STORAGE= apply_cluster ;;
  rate)
    for iv in ${*:-60s 15s}; do
      INTERVAL=$iv apply_cluster; INTERVAL=$iv apply_node
      INTERVAL=$iv settle_and_measure "rate: $(current_pods) idle pods, $iv interval" rate
    done
    apply_cluster; apply_node ;;
  restore)
    set_load 0
    IMAGE= "$here/gen-cluster-collector.py" | oc apply -f - >/dev/null
    sed -e '/^  image: registry.redhat.io/d' 02-node-collector.yaml | oc apply -f - >/dev/null
    log "collectors export to the vendor Prometheus again" ;;
  *) echo "unknown phase $phase"; exit 1 ;;
esac
log "phase $phase done"
