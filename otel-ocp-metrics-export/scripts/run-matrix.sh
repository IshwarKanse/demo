#!/bin/bash
# Run the extended benchmark matrix and export every run for scripts/render-charts.py.
#
# usage: scripts/run-matrix.sh <results dir> [phase...]
#   phases, in the default order:
#     baseline     platform Prometheus without remote write (run BEFORE the CMO config maps are applied)
#     remotewrite  apply the CMO config maps and wait for the first remote write samples
#     series       series-count tiers at a 30 s scrape interval: 0, 4, 10, 20 load pods, 1 replica
#     rate         sample-rate tiers at a fixed series count (10 load pods): 60 s and 15 s scrape interval
#     replicas     20 load pods with 2 collector replicas
#     churn        series turnover: rotating churn series plus a rollout of the load deployment every 10 min
#     compaction   one long steady-state window (default 3 h) so that TSDB compactions fall inside it
#     outage       scripts/outage-test.sh followed by an export of the outage window
# prerequisites: manifests 00, 01, 02, 05 and 06 applied, KUBECONFIG set, the operator installed.
# env: SETTLE_MIN (5), WINDOW_MIN (20), COMPACTION_MIN (180), CHURN_MIN (40), OUTAGE_MIN (5),
#      COLLECTOR_IMAGE (patched into the collector CR when set), SERIES_TIERS (load pod counts of the
#      series phase, default "0 4 10 20"; one pod = 25,000 series)
set -euo pipefail
cd "$(dirname "$0")/.."
dir=$1; shift
phases=("$@"); [ ${#phases[@]} -gt 0 ] || phases=(baseline remotewrite series rate replicas churn compaction outage)
settle=${SETTLE_MIN:-5}; window=${WINDOW_MIN:-20}
ns=otel-metrics-export; lns=otel-metrics-load
mkdir -p "$dir"; table="$dir/table.md"
log() { echo "== $(date -u +%FT%TZ) $*"; }
collector_replicas() {
  if [ -n "${COLLECTOR_IMAGE:-}" ]; then
    oc patch opentelemetrycollector otel -n "$ns" --type=merge -p "{\"spec\":{\"image\":\"${COLLECTOR_IMAGE}\",\"replicas\":$1}}"
  else
    oc patch opentelemetrycollector otel -n "$ns" --type=merge -p "{\"spec\":{\"replicas\":$1}}"
  fi
  oc rollout status deploy/otel-collector -n "$ns" --timeout=5m
}
set_load() {
  oc scale deploy/avalanche-load -n "$lns" --replicas="$1"
  [ "$1" -gt 0 ] && oc rollout status deploy/avalanche-load -n "$lns" --timeout=5m || true
}
set_interval() { oc patch servicemonitor avalanche-load -n "$lns" --type=json -p "[{\"op\":\"replace\",\"path\":\"/spec/endpoints/0/interval\",\"value\":\"$1\"}]"; }
measure() {  # label kind window_min extra_series
  log "settling ${settle} min, measuring $3 min: $1"
  sleep $(( (settle + $3) * 60 ))
  end=$(date +%s)
  NAMESPACE=$ns COLLECTOR=otel scripts/collect.sh "$1" "$3" "$end" "$table" >/dev/null
  NAMESPACE=$ns COLLECTOR=otel EXTRA_SERIES=$4 scripts/export-series.sh "$1" "$2" "$3" "$end" "$dir"
}
rw_active() { v=$(scripts/pq.sh 'sum(rate(prometheus_remote_storage_samples_total{remote_name="otel-collector"}[2m]))' | awk -F'=> ' '{print int($2)}'); echo "${v:-0}"; }
for phase in "${phases[@]}"; do
  log "phase $phase"
  case $phase in
    baseline)
      if [ -n "$(oc get prometheus k8s -n openshift-monitoring -o jsonpath='{.spec.remoteWrite}')" ]; then
        echo "   remote write is already configured on the platform Prometheus; skipping the baseline"; continue
      fi
      set_load 0; collector_replicas 1
      measure "baseline: no remote write, 0 load pods" baseline "$window" 0 ;;
    remotewrite)
      oc apply -f manifests/03-cluster-monitoring-config.yaml -f manifests/04-user-workload-monitoring-config.yaml
      log "waiting for the first remote write samples (up to 15 min)"
      for i in $(seq 1 90); do [ "$(rw_active)" -gt 0 ] && break; sleep 10; done
      [ "$(rw_active)" -gt 0 ] || { echo "no remote write samples after 15 min"; exit 1; } ;;
    series)
      collector_replicas 1; set_interval 30s
      for pods in ${SERIES_TIERS:-0 4 10 20}; do set_load "$pods"; measure "series: $pods load pods, 30 s interval, 1 replica" steady "$window" $((pods*25000)); done ;;
    rate)
      collector_replicas 1; set_load 10
      for iv in 60s 15s; do set_interval "$iv"; measure "rate: 10 load pods, $iv interval, 1 replica" steady "$window" 250000; done
      set_interval 30s ;;
    replicas)
      set_interval 30s; set_load 20; collector_replicas 2
      measure "replicas: 20 load pods, 30 s interval, 2 replicas" steady "$window" 500000
      collector_replicas 1 ;;
    churn)
      cm=${CHURN_MIN:-40}; set_interval 30s; set_load 4; collector_replicas 1
      oc scale deploy/avalanche-churn -n "$lns" --replicas=4; oc rollout status deploy/avalanche-churn -n "$lns" --timeout=5m
      log "churn for ${cm} min: 4 rotating churn pods, avalanche-load restarted every 10 min"
      sleep $((settle*60))
      for i in $(seq 1 $((cm/10))); do oc rollout restart deploy/avalanche-load -n "$lns"; sleep 600; done
      end=$(date +%s)
      NAMESPACE=$ns COLLECTOR=otel scripts/collect.sh "churn: 4 load pods restarted every 10 min + 4 churn pods" "$cm" "$end" "$table" >/dev/null
      NAMESPACE=$ns COLLECTOR=otel EXTRA_SERIES=120000 scripts/export-series.sh "churn: 4 load pods restarted every 10 min + 4 churn pods" churn "$cm" "$end" "$dir"
      oc scale deploy/avalanche-churn -n "$lns" --replicas=0 ;;
    compaction)
      cmp=${COMPACTION_MIN:-180}; set_interval 30s; set_load 10; collector_replicas 1
      STEP=60 measure "compaction: 10 load pods, 30 s interval, ${cmp} min" compaction "$cmp" 250000 ;;
    outage)
      om=${OUTAGE_MIN:-5}; set_interval 30s; set_load 8; collector_replicas 1
      sleep $((settle*60))
      scripts/outage-test.sh "$om" "$table"
      NAMESPACE=$ns COLLECTOR=otel EXTRA_SERIES=200000 scripts/export-series.sh "outage: ${om} min sink outage, 8 load pods" outage $((om+12)) "$(date +%s)" "$dir" ;;
    *) echo "unknown phase $phase"; exit 1 ;;
  esac
done
log "matrix done; render with: .venv/bin/python scripts/render-charts.py $dir"
