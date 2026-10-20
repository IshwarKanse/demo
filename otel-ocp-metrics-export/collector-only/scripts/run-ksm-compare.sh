#!/bin/bash
# k8s_cluster receiver against kube-state-metrics with a large object inventory.
#
# usage: scripts/run-ksm-compare.sh <results dir> <phase>
#   baseline     BASE_MIN (10) minutes with the empty inventory; records the collector's first-inventory time
#   create       creates the inventory (load/gen-objects.py), records the time until both see it, exports the window
#   steady       WINDOW_MIN (20) minutes with the full inventory
#   restart      deletes the collector pod and records the time until it has the full inventory again (10 min window)
#   churn        CHURN_CYCLES (3) delete-and-recreate cycles of the deployments, 7 minutes apart, exported as one window
#   steady2      10 minutes after the churn
#   timeline     one export over the whole experiment (all markers) for the timeline chart, then the audit log counts
#   cleanup      deletes the inventory namespace, the cluster resource quotas and the k8s_cluster-only collector
# prerequisites: 08-k8scluster-collector.yaml, 06-vendor-prometheus.yaml and 07-uwm-podmonitor.yaml applied,
# KUBECONFIG set. env: NAMESPACE (otel-platform-metrics), LOAD_NS (otel-load-objects), SETTLE_MIN (3)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../.." && pwd); cd "$here/.."
dir=$1; phase=$2; mkdir -p "$dir/raw"; dir=$(cd "$dir" && pwd)
ns=${NAMESPACE:-otel-platform-metrics}; lns=${LOAD_NS:-otel-load-objects}; settle=${SETTLE_MIN:-3}
state="$dir/raw/phases.env"; touch "$state"; . "$state"
log() { echo "== $(date -u +%FT%TZ) $*"; }
save() { echo "$1=$2" >> "$state"; }
vq() {  # instant query against the vendor Prometheus
  curl -s "http://localhost:19090/api/v1/query" --data-urlencode "query=$1" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else 0)'
}
tq() { "$root/scripts/pq.sh" "$1" | awk -F'=> ' 'NR==1{print int($2)}'; }
pf_start() { oc port-forward -n "$ns" svc/vendor-prometheus 19090:9090 >/dev/null 2>&1 & PF=$!; curl -s --retry 10 --retry-connrefused --retry-delay 1 -o /dev/null http://localhost:19090/-/ready; }
pf_stop() { kill "${PF:-0}" 2>/dev/null; }
vendor_inventory() {  # <slug> <start> <end>: the inventory the collector has seen, per kind, as a CSV series
  local out="$dir/raw/$1"; mkdir -p "$out"; pf_start
  { echo "ts,series,value"
    for kv in deployments:k8s_deployment_desired replicasets:k8s_replicaset_desired jobs:k8s_job_desired_successful_pods cronjobs:k8s_cronjob_active_jobs hpas:k8s_hpa_max_replicas quotas:k8s_resource_quota_hard_limit clusterquotas:openshift_clusterquota_limit; do
      curl -s "http://localhost:19090/api/v1/query_range" --data-urlencode "query=count(${kv#*:}{collector=\"otel-k8scluster\",k8s_namespace_name=\"$lns\"}) or count(${kv#*:}{collector=\"otel-k8scluster\"}) * 0" --data-urlencode "start=$2" --data-urlencode "end=$3" --data-urlencode "step=15" \
        | python3 -c "import sys,json; [print(f'{int(float(t))},kind=${kv%%:*},{v}') for s in json.load(sys.stdin)['data']['result'] for t,v in s['values']]"
    done; } > "$out/collector_inventory.csv"; pf_stop
}
export_run() {  # <label> <kind> <start> <end> [markers]
  local win=$(( ($4 - $3 + 59) / 60 ))
  PROFILE=k8scluster VARIANT=k8scluster CONFIG="k8s_cluster receiver only, 30 s interval, vendor Prometheus backend" STEP=${STEP:-15} MARKERS="${5:-}" "$root/scripts/export-series.sh" "$1" "$2" "$win" "$4" "$dir"
  vendor_inventory "$(echo "$1" | tr -c 'A-Za-z0-9\n' '-' | sed -E 's/-+/-/g; s/^-//; s/-$//' | tr 'A-Z' 'a-z')" "$3" "$4"
}
wait_inventory() {  # <expected deployments> <since ts> -> prints "collector_s ksm_s"
  local n=$1 since=$2 tc="" tk="" now
  pf_start
  for i in $(seq 1 180); do
    now=$(date +%s)
    [ -z "$tc" ] && [ "$(vq "count(k8s_deployment_desired{collector=\"otel-k8scluster\",k8s_namespace_name=\"$lns\"})")" -ge "$n" ] 2>/dev/null && tc=$((now - since))
    [ -z "$tk" ] && [ "$(tq "count(kube_deployment_spec_replicas{namespace=\"$lns\"})")" -ge "$n" ] 2>/dev/null && tk=$((now - since))
    [ -n "$tc" ] && [ -n "$tk" ] && break
    sleep 10
  done
  pf_stop; echo "${tc:-none} ${tk:-none}"
}
apply_objects() {  # [--only kinds]
  load/gen-objects.py --ns "$lns" "$@" | oc apply --server-side --force-conflicts -f - >/dev/null 2>"$dir/raw/apply-errors.log" || log "apply reported errors: $(wc -l < "$dir/raw/apply-errors.log") lines"
}
log "phase $phase"
case $phase in
  baseline)
    pod_start=$(oc get pods -n "$ns" -l app.kubernetes.io/instance=$ns.otel-k8scluster -o jsonpath='{.items[0].status.startTime}')
    start=$(date +%s); save BASELINE_START "$start"
    sleep $(( ${BASE_MIN:-10} * 60 )); end=$(date +%s); save BASELINE_END "$end"
    export_run "baseline: empty inventory" steady "$start" "$end"
    log "collector pod started $pod_start; baseline exported" ;;
  create)
    start=$(date +%s); save CREATE_START "$start"
    log "creating the inventory"
    apply_objects
    created=$(date +%s); save CREATE_END "$created"; log "inventory applied in $((created - start)) s"
    read -r tc tk <<<"$(wait_inventory ${DEPLOYMENTS:-2000} "$created")"
    save CREATE_SEEN_COLLECTOR "$tc"; save CREATE_SEEN_KSM "$tk"; log "full inventory seen by the collector after ${tc} s, by kube-state-metrics after ${tk} s (from the end of the apply)"
    sleep $((settle * 60)); end=$(date +%s); save CREATE_PHASE_END "$end"
    export_run "create: inventory applied" steady "$start" "$end" "apply start=$start;apply end=$created" ;;
  steady)
    start=$(date +%s); save STEADY_START "$start"; sleep $(( ${WINDOW_MIN:-20} * 60 )); end=$(date +%s); save STEADY_END "$end"
    export_run "steady: full inventory" steady "$start" "$end" ;;
  restart)
    start=$(date +%s); save RESTART_START "$start"
    oc delete pod -n "$ns" -l app.kubernetes.io/instance=$ns.otel-k8scluster --wait=false >/dev/null
    sleep 5; oc rollout status deploy/otel-k8scluster-collector -n "$ns" --timeout=5m >/dev/null
    pod_start=$(date -u -j -f %Y-%m-%dT%H:%M:%SZ "$(oc get pods -n "$ns" -l app.kubernetes.io/instance=$ns.otel-k8scluster -o jsonpath='{.items[0].status.startTime}')" +%s 2>/dev/null || date +%s)
    # the old series stop; wait until the new pod reports the full inventory (the count is per scrape, old samples age out after 5 min: use a fresh series name check via the accepted points instead)
    pf_start; t=""
    for i in $(seq 1 120); do
      v=$(curl -s "http://localhost:19090/api/v1/query" --data-urlencode "query=count(k8s_deployment_desired{collector=\"otel-k8scluster\",k8s_namespace_name=\"$lns\"} unless (timestamp(k8s_deployment_desired{collector=\"otel-k8scluster\",k8s_namespace_name=\"$lns\"}) < $pod_start))" | python3 -c 'import sys,json; r=json.load(sys.stdin)["data"]["result"]; print(r[0]["value"][1] if r else 0)')
      [ "${v:-0}" -ge "${DEPLOYMENTS:-2000}" ] 2>/dev/null && t=$(( $(date +%s) - pod_start )) && break; sleep 5
    done; pf_stop
    save RESTART_SEEN_COLLECTOR "${t:-none}"; log "after a restart the collector had the full inventory after ${t:-none} s"
    sleep $(( 10 * 60 - ${t:-0} > 0 ? 10 * 60 - ${t:-0} : 60 )); end=$(date +%s); save RESTART_END "$end"
    export_run "restart: collector pod recreated" steady "$start" "$end" "pod start=$pod_start" ;;
  churn)
    start=$(date +%s); save CHURN_START "$start"; markers=""
    for c in $(seq 1 ${CHURN_CYCLES:-3}); do
      t=$(date +%s); markers="${markers:+$markers;}recreate $c=$t"
      oc delete deploy -n "$lns" -l load-kind=deployment --wait=false >/dev/null 2>&1
      sleep 60
      apply_objects --only deployments
      log "churn cycle $c: deployments deleted and recreated"
      sleep $(( 7 * 60 - 60 ))
    done
    end=$(date +%s); save CHURN_END "$end"; save CHURN_MARKERS "$markers"
    export_run "churn: deployments recreated ${CHURN_CYCLES:-3} times" steady "$start" "$end" "$markers" ;;
  steady2)
    start=$(date +%s); save STEADY2_START "$start"; sleep $(( 10 * 60 )); end=$(date +%s); save STEADY2_END "$end"
    export_run "steady2: after the churn" steady "$start" "$end" ;;
  timeline)
    . "$state"
    m="apply start=$CREATE_START;apply end=$CREATE_END;steady=$STEADY_START;restart=$RESTART_START;${CHURN_MARKERS};steady2=$STEADY2_START"
    STEP=30 export_run "timeline: whole experiment" timeline "$BASELINE_START" "$STEADY2_END" "$m"
    log "fetching the audit logs of the control plane nodes"
    tmp=$(mktemp -d); i=0
    for node in $(oc get nodes -l node-role.kubernetes.io/control-plane -o name); do
      i=$((i+1)); n=${node#node/}
      oc adm node-logs "$n" --path=kube-apiserver/audit.log > "$tmp/audit-$i.log" 2>/dev/null
      prev=$(oc adm node-logs "$n" --path=kube-apiserver/ 2>/dev/null | grep '^audit-' | sort | tail -1)
      [ -n "$prev" ] && oc adm node-logs "$n" --path="kube-apiserver/$prev" > "$tmp/audit-$i-prev.log" 2>/dev/null
    done
    "$here/audit-requests.py" "$dir" "$tmp"/audit-*.log; rm -rf "$tmp" ;;
  export-baseline)  # re-export the baseline window from the saved timestamps (the first run failed on an unset variable)
    export_run "baseline: empty inventory" steady "$BASELINE_START" "$BASELINE_END" ;;
  cleanup)
    oc delete clusterresourcequota -l app.kubernetes.io/part-of=otel-load-objects --wait=false >/dev/null 2>&1
    oc delete namespace "$lns" --wait=false >/dev/null 2>&1
    oc delete -f 08-k8scluster-collector.yaml >/dev/null 2>&1
    log "inventory namespace, cluster resource quotas and the k8s_cluster-only collector deleted" ;;
  *) echo "unknown phase $phase"; exit 1 ;;
esac
log "phase $phase done"
