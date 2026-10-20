#!/bin/bash
# Scale ladder: the k8s_cluster receiver against kube-state-metrics with a production-sized object inventory.
# The inventory grows in steps (units of 1,000 created objects in one namespace each, load/loader.py run as a Job
# in the cluster by load/loader-driver.yaml); every step runs the same phases as scripts/run-ksm-compare.sh and
# the audit log events of both clients are pulled right after each phase, before the API server rotates them.
#
# usage: scripts/run-scale-ladder.sh <results dir> <phase> [units]
#   setup            applies the k8s_cluster-only collector, the loader driver and raises the vendor Prometheus limit
#   baseline         BASE_MIN (5) minutes with the empty inventory (step 0)
#   limit <mem>      sets the memory limit of the collector (memory_limiter follows: percentages) and waits for the rollout
#   create <units>   grows the inventory to <units> (from the last step), waits until both clients see it, exports
#   steady <units>   WINDOW_MIN (20) minutes with the full inventory
#   restart <units>  deletes the collector pod; time to the full inventory again, LIST events from the audit log
#   restart-ksm <units>  the same for kube-state-metrics (CMO recreates the pod; the inventory is seen through the sample count of the new target)
#   churn <units>    one cycle: the deployments of the first 10 % of the namespaces deleted and recreated
#   steady2 <units>  10 minutes after the churn
#   step <units>     create, steady, restart, restart-ksm, churn, steady2 in one go (stops if the control plane is at its limit)
#   timeline         one export over the whole ladder with the step markers
#   cleanup          deletes the inventory namespaces, the cluster resource quotas, the loader driver and the collector
# prerequisites: 06-vendor-prometheus.yaml and 07-uwm-podmonitor.yaml applied, KUBECONFIG set.
# env: NAMESPACE (otel-platform-metrics), SETTLE_MIN (3), WINDOW_MIN (20), BASE_MIN (5), WORKERS (24)
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); root=$(cd "$here/../.." && pwd); cd "$here/.."
dir=$1; phase=$2; units=${3:-}; mkdir -p "$dir/raw/audit" "$dir/raw/loader"; dir=$(cd "$dir" && pwd)
ns=${NAMESPACE:-otel-platform-metrics}; dns=otel-load-driver; settle=${SETTLE_MIN:-3}; workers=${WORKERS:-24}
DEP_PER_UNIT=150; CM_PER_UNIT=400; SEC_PER_UNIT=263; SVC_PER_UNIT=100; JOB_PER_UNIT=50; CRON_PER_UNIT=30; QUOTA_PER_UNIT=6
state="$dir/raw/phases.env"; touch "$state"; . "$state"
log() { echo "== $(date -u +%FT%TZ) $*"; }
save() { echo "$1=\"$2\"" >> "$state"; }
tag() { echo "${units}k"; }
# bash 3.2 (macOS) brace-expands a comma inside {...} when the query is nested in "$( ... "..." ... )": every query
# is put into a variable first and passed as "$q", never written inline inside a nested command substitution.
vq() {  # instant query against the vendor Prometheus (port-forward must be up); 0 on any error
  curl -s "http://localhost:19090/api/v1/query" --data-urlencode "query=$1" | python3 -c 'import sys,json
try:
    r=json.load(sys.stdin)["data"]["result"]; print(int(float(r[0]["value"][1])) if r else 0)
except Exception: print(0)'
}
tq() { "$root/scripts/pq.sh" "$1" | awk -F'=> ' 'NR==1{print int($2+0)}'; }
first_reach() {  # <vendor|thanos> <query> <n> <since> <until>: seconds after <since> until the range query first reaches n ("none")
  local q=$2 n=$3 since=$4 until=$5 out
  if [ "$1" = vendor ]; then
    out=$(curl -s "http://localhost:19090/api/v1/query_range" --data-urlencode "query=$q" --data-urlencode "start=$since" --data-urlencode "end=$until" --data-urlencode "step=5")
  else
    local AUTH CA HOST; AUTH=$(mktemp); chmod 600 "$AUTH"; CA=$(mktemp)
    printf 'Authorization: Bearer %s\n' "$(oc create token prometheus-k8s -n openshift-monitoring --duration=10m)" > "$AUTH"
    HOST=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')
    oc get configmap default-ingress-cert -n openshift-config-managed -o jsonpath='{.data.ca-bundle\.crt}' > "$CA"
    out=$(curl -s --cacert "$CA" -H @"$AUTH" "https://$HOST/api/v1/query_range" --data-urlencode "query=$q" --data-urlencode "start=$since" --data-urlencode "end=$until" --data-urlencode "step=5"); rm -f "$AUTH" "$CA"
  fi
  python3 -c 'import sys,json
n=int(sys.argv[1]); since=int(sys.argv[2])
try:
    for s in json.load(sys.stdin)["data"]["result"]:
        for t,v in s["values"]:
            if float(v) >= n: print(int(float(t)) - since); sys.exit()
except Exception: pass
print("none")' "$n" "$since" <<<"$out"
}
pf_start() { oc port-forward -n "$ns" svc/vendor-prometheus 19090:9090 >/dev/null 2>&1 & PF=$!; curl -s --retry 10 --retry-connrefused --retry-delay 1 -o /dev/null http://localhost:19090/-/ready; }
pf_stop() { kill "${PF:-0}" 2>/dev/null; }
vendor_inventory() {  # <slug> <start> <end>: the inventory the collector has seen, per kind, as a CSV series
  local out="$dir/raw/$1"; mkdir -p "$out"; pf_start
  { echo "ts,series,value"
    for kv in deployments:k8s_deployment_desired replicasets:k8s_replicaset_desired jobs:k8s_job_desired_successful_pods cronjobs:k8s_cronjob_active_jobs hpas:k8s_hpa_max_replicas quotas:k8s_resource_quota_hard_limit clusterquotas:openshift_clusterquota_limit namespaces:k8s_namespace_phase; do
      curl -s "http://localhost:19090/api/v1/query_range" --data-urlencode "query=count(${kv#*:}{collector=\"otel-k8scluster\",k8s_namespace_name=~\"otel-load-.*\"}) or count(${kv#*:}{collector=\"otel-k8scluster\"}) * 0" --data-urlencode "start=$2" --data-urlencode "end=$3" --data-urlencode "step=15" \
        | python3 -c "import sys,json; [print(f'{int(float(t))},kind=${kv%%:*},{v}') for s in json.load(sys.stdin)['data']['result'] for t,v in s['values']]"
    done; } > "$out/collector_inventory.csv"; pf_stop
}
export_run() {  # <label> <kind> <start> <end> [markers]
  local win=$(( ($4 - $3 + 59) / 60 ))
  PROFILE=k8scluster-scale VARIANT=k8scluster UNITS=${units:-0} CONFIG="k8s_cluster receiver only, 30 s interval, vendor Prometheus backend, collector memory limit $(collector_limit)" STEP=${STEP:-15} MARKERS="${5:-}" "$root/scripts/export-series.sh" "$1" "$2" "$win" "$4" "$dir"
  vendor_inventory "$(echo "$1" | tr -c 'A-Za-z0-9\n' '-' | sed -E 's/-+/-/g; s/^-//; s/-$//' | tr 'A-Z' 'a-z')" "$3" "$4"
}
collector_limit() { oc get opentelemetrycollector otel-k8scluster -n "$ns" -o jsonpath='{.spec.resources.limits.memory}' 2>/dev/null; }
collector_pod() { oc get pods -n "$ns" -l app.kubernetes.io/instance=$ns.otel-k8scluster -o jsonpath='{.items[0].metadata.name}' 2>/dev/null; }
pod_start_ts() { date -u -j -f %Y-%m-%dT%H:%M:%SZ "$(oc get pod -n "$1" "$2" -o jsonpath='{.status.startTime}')" +%s 2>/dev/null || date +%s; }
cp_snapshot() {  # <tag>: control plane health, one JSON line; returns 1 when the control plane is at its limit
  local q; q=$(python3 - "$root" "$1" <<'PY'
import json, subprocess, sys, time
root, tag = sys.argv[1], sys.argv[2]
def pq(q):
    out = subprocess.run([f"{root}/scripts/pq.sh", q], capture_output=True, text=True).stdout.strip().splitlines()
    return float(out[0].split("=> ")[1]) if out and "=> " in out[0] else None
m = {"tag": tag, "ts": int(time.time()),
     "apiserver_wss_max_pod_gib": pq('max(container_memory_working_set_bytes{namespace="openshift-kube-apiserver",container="kube-apiserver"})'),
     "apiserver_cpu_cores": pq('sum(rate(container_cpu_usage_seconds_total{namespace="openshift-kube-apiserver",container="kube-apiserver"}[5m]))'),
     "etcd_db_mib": pq('max(etcd_mvcc_db_total_size_in_bytes)'), "etcd_wss_max_pod_gib": pq('max(container_memory_working_set_bytes{namespace="openshift-etcd",container="etcd"})'),
     "etcd_fsync_p99_s": pq('histogram_quantile(0.99, sum by (le) (rate(etcd_disk_wal_fsync_duration_seconds_bucket[5m])))'),
     "etcd_leader_changes_1h": pq('max(increase(etcd_server_leader_changes_seen_total[1h]))'),
     "apiserver_429_s": pq('sum(rate(apiserver_request_total{code="429"}[5m]))'),
     "list_p99_s": pq('histogram_quantile(0.99, sum by (le) (rate(apiserver_request_duration_seconds_bucket{verb="LIST"}[5m])))'),
     "kcm_wss_max_pod_gib": pq('max(container_memory_working_set_bytes{namespace="openshift-kube-controller-manager",container="kube-controller-manager"})'),
     "storage_objects": pq('sum(max by (resource) (apiserver_storage_objects))'), "master_memory_pressure": pq('max(kube_node_status_condition{condition="MemoryPressure",status="true",node=~".*"} * on (node) group_left() kube_node_role{role="control-plane"})'),
     "prometheus_k8s_wss_max_gib": pq('max(container_memory_working_set_bytes{namespace="openshift-monitoring",pod=~"prometheus-k8s-.*",container="prometheus"})')}
for k in ("apiserver_wss_max_pod_gib", "etcd_wss_max_pod_gib", "kcm_wss_max_pod_gib", "prometheus_k8s_wss_max_gib"):
    m[k] = round(m[k] / 2**30, 2) if m[k] is not None else None
m["etcd_db_mib"] = round(m["etcd_db_mib"] / 2**20, 1) if m["etcd_db_mib"] else None
# masters are m6i.xlarge (14.2 GiB allocatable): the API server, etcd and the controller manager share them
m["at_limit"] = [k for k, v in (("apiserver_wss_max_pod_gib", 9), ("etcd_fsync_p99_s", 0.1), ("apiserver_429_s", 1), ("list_p99_s", 60), ("master_memory_pressure", 0.5), ("etcd_db_mib", 6000)) if (m.get(k) or 0) > v]
print(json.dumps(m))
PY
)
  echo "$q" >> "$dir/raw/control-plane.jsonl"; log "control plane: $q"
  [ "$(echo "$q" | python3 -c 'import sys,json; print(len(json.load(sys.stdin)["at_limit"]))')" = 0 ]
}
loader_job() {  # <tag> <loader args...>: runs load/loader.py as a Job in the cluster, saves the log, prints the summary JSON
  local t=$1; shift; local name="loader-$t-$(date +%s)"; local args=""
  for a in "$@"; do args="$args, \"$a\""; done
  oc create -f - >/dev/null <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $name
  namespace: $dns
  labels:
    app.kubernetes.io/part-of: otel-load-objects
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels:
        app.kubernetes.io/part-of: otel-load-objects
    spec:
      serviceAccountName: loader
      restartPolicy: Never
      containers:
      - name: loader
        image: registry.access.redhat.com/ubi9/python-312:latest
        command: ["python3", "-u", "/opt/loader/loader.py"$args]
        volumeMounts:
        - name: script
          mountPath: /opt/loader
        resources:
          requests:
            cpu: "1"
            memory: 512Mi
          limits:
            memory: 2Gi
      volumes:
      - name: script
        configMap:
          name: loader
EOF
  for i in $(seq 1 1440); do
    s=$(oc get job "$name" -n "$dns" -o jsonpath='{.status.succeeded}/{.status.failed}' 2>/dev/null)
    [ "$s" = "1/" ] || [ "${s#*/}" = 1 ] && break; sleep 5
  done
  oc logs "job/$name" -n "$dns" > "$dir/raw/loader/$t.log" 2>&1
  tail -1 "$dir/raw/loader/$t.log"
}
pull_audit() {  # <tag> <start> <end>: the audit events of the two clients in the window from every master (ResponseStarted and
  # ResponseComplete: the initial-events watch of a client-go watch list stays open for minutes, so its only event in the window is the start)
  local t=$1 start=$2 end=$3 tmp; tmp=$(mktemp -d); local out="$dir/raw/audit/$t.jsonl"; : > "$out"
  local since; since=$(date -u -r "$((start - 120))" +%Y-%m-%dT%H-%M-%S)
  for node in $(oc get nodes -l node-role.kubernetes.io/control-plane -o name); do
    local n=${node#node/} files="audit.log"
    for f in $(oc adm node-logs "$n" --path=kube-apiserver/ 2>/dev/null | grep '^audit-' | sort); do
      [[ "${f#audit-}" > "$since" ]] && files="$files $f"
    done
    for f in $files; do
      oc adm node-logs "$n" --path="kube-apiserver/$f" 2>/dev/null | grep -E '"stage":"Response(Started|Complete)"' | grep -E 'serviceaccount:(otel-platform-metrics:otel-k8scluster|openshift-monitoring:kube-state-metrics)"' >> "$tmp/events.jsonl"
    done
  done
  python3 - "$tmp/events.jsonl" "$start" "$end" "$out" <<'PY'
import json, sys
from datetime import datetime, timezone
src, start, end, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
seen = set(); n = 0
with open(out, "w") as fh:
    for line in open(src, errors="replace"):
        try: e = json.loads(line)
        except ValueError: continue
        ts = datetime.strptime(e["requestReceivedTimestamp"][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
        key = (e["auditID"], e.get("stage"))
        if start - 1 <= ts <= end + 1 and key not in seen:
            seen.add(key); fh.write(line if line.endswith("\n") else line + "\n"); n += 1
print(f"{n} audit events in {out}")
PY
  rm -rf "$tmp"
}
wait_inventory() {  # <expected deployments> <since ts> -> prints "collector_s ksm_s"
  local n=$1 since=$2 tc="" tk="" now v
  local qc='count(k8s_deployment_desired{collector="otel-k8scluster",k8s_namespace_name=~"otel-load-.*"})' qk='count(kube_deployment_spec_replicas{namespace=~"otel-load-.*"})'
  pf_start
  for i in $(seq 1 360); do
    now=$(date +%s)
    if [ -z "$tc" ]; then v=$(vq "$qc"); [ "${v:-0}" -ge "$n" ] && tc=$((now - since)); fi
    if [ -z "$tk" ]; then v=$(tq "$qk"); [ "${v:-0}" -ge "$n" ] && tk=$((now - since)); fi
    [ -n "$tc" ] && [ -n "$tk" ] && break
    sleep 10
  done
  # the exact times from the stored series (5 s resolution on the vendor side, the 30 s scrape on the platform side)
  local tc2 tk2; tc2=$(first_reach vendor "$qc" "$n" "$since" "$now"); tk2=$(first_reach thanos "$qk" "$n" "$since" "$now")
  pf_stop; echo "${tc2:-${tc:-none}} ${tk2:-${tk:-none}}"
}
expected_deployments() { echo $(( ${units:-0} * DEP_PER_UNIT )); }
need_units() { [ -n "$units" ] || { echo "phase $phase needs the units argument"; exit 1; }; }
log "phase $phase ${units:+(step ${units}k)}"
case $phase in
  setup)
    oc apply -f 08-k8scluster-collector.yaml >/dev/null
    oc apply -f load/loader-driver.yaml >/dev/null
    oc create configmap loader -n "$dns" --from-file=loader.py=load/loader.py --dry-run=client -o yaml | oc apply -f - >/dev/null
    # the vendor stand-in keeps every series of the inventory (promote_all_resource_attributes): room for ~400k series
    oc set resources deploy vendor-prometheus -n "$ns" --limits=memory=24Gi --requests=memory=4Gi >/dev/null
    oc rollout status deploy/vendor-prometheus -n "$ns" --timeout=5m >/dev/null
    oc rollout status deploy/otel-k8scluster-collector -n "$ns" --timeout=5m >/dev/null
    save LADDER_START "$(date +%s)"; save UNITS_DONE 0
    log "collector (limit $(collector_limit)), loader driver and vendor Prometheus ready" ;;
  baseline)
    units=0; start=$(date +%s); save BASELINE_START "$start"
    sleep $(( ${BASE_MIN:-5} * 60 )); end=$(date +%s); save BASELINE_END "$end"
    export_run "0k steady: empty inventory" steady "$start" "$end"; cp_snapshot "0k-steady" || true ;;
  limit)
    need_units; mem=$units; units=""
    oc patch opentelemetrycollector otel-k8scluster -n "$ns" --type merge -p "{\"spec\":{\"resources\":{\"limits\":{\"memory\":\"$mem\"}}}}" >/dev/null
    sleep 10; oc rollout status deploy/otel-k8scluster-collector -n "$ns" --timeout=10m >/dev/null
    log "collector memory limit now $(collector_limit)" ;;
  create)
    need_units; from=${UNITS_DONE:-0}; t=$(tag)
    cp_snapshot "$t-before-create" || { log "the control plane is at its limit before step $t, stopping the ladder"; exit 2; }
    start=$(date +%s); save "CREATE_START_$t" "$start"; log "growing the inventory from $from to $units units"
    summary=$(loader_job "$t-create" create --from "$from" --to "$units" --workers "$workers"); log "loader: $summary"
    created=$(date +%s); save "CREATE_END_$t" "$created"; save UNITS_DONE "$units"
    read -r tc tk <<<"$(wait_inventory "$(expected_deployments)" "$created")"
    save "CREATE_SEEN_COLLECTOR_$t" "$tc"; save "CREATE_SEEN_KSM_$t" "$tk"; log "full inventory seen by the collector after ${tc} s, by kube-state-metrics after ${tk} s (from the end of the loader)"
    sleep $((settle * 60)); end=$(date +%s); save "CREATE_PHASE_END_$t" "$end"
    export_run "$t create: inventory grown to $units units" steady "$start" "$end" "loader start=$start;loader end=$created"
    pull_audit "$t-create" "$start" "$end"; cp_snapshot "$t-after-create" || true ;;
  create-finish)  # finishes an interrupted create phase from the saved loader timestamps
    need_units; t=$(tag); start=$(eval echo "\$CREATE_START_$t"); created=$(eval echo "\$CREATE_END_$t"); now=$(date +%s)
    qc='count(k8s_deployment_desired{collector="otel-k8scluster",k8s_namespace_name=~"otel-load-.*"})'; qk='count(kube_deployment_spec_replicas{namespace=~"otel-load-.*"})'
    pf_start; tc=$(first_reach vendor "$qc" "$(expected_deployments)" "$created" "$now"); pf_stop; tk=$(first_reach thanos "$qk" "$(expected_deployments)" "$created" "$now")
    save "CREATE_SEEN_COLLECTOR_$t" "$tc"; save "CREATE_SEEN_KSM_$t" "$tk"; log "full inventory seen by the collector after ${tc} s, by kube-state-metrics after ${tk} s (from the end of the loader, from the stored series)"
    remaining=$(( created + settle * 60 - now )); [ "$remaining" -gt 0 ] && sleep "$remaining"
    end=$(date +%s); save "CREATE_PHASE_END_$t" "$end"
    export_run "$t create: inventory grown to $units units" steady "$start" "$end" "loader start=$start;loader end=$created"
    pull_audit "$t-create" "$start" "$end"; cp_snapshot "$t-after-create" || true ;;
  steady)
    need_units; t=$(tag); start=$(date +%s); save "STEADY_START_$t" "$start"; sleep $(( ${WINDOW_MIN:-20} * 60 )); end=$(date +%s); save "STEADY_END_$t" "$end"
    export_run "$t steady: full inventory" steady "$start" "$end"; pull_audit "$t-steady" "$start" "$end"; cp_snapshot "$t-steady" || true ;;
  restart)
    need_units; t=$(tag); start=$(date +%s); save "RESTART_START_$t" "$start"
    oc delete pod -n "$ns" -l app.kubernetes.io/instance=$ns.otel-k8scluster --wait=false >/dev/null
    sleep 5; oc rollout status deploy/otel-k8scluster-collector -n "$ns" --timeout=10m >/dev/null
    pod=$(collector_pod); pod_start=$(pod_start_ts "$ns" "$pod")
    pf_start; tc=""; n=$(expected_deployments)
    q='count(k8s_deployment_desired{collector="otel-k8scluster",k8s_namespace_name=~"otel-load-.*"} unless (timestamp(k8s_deployment_desired{collector="otel-k8scluster",k8s_namespace_name=~"otel-load-.*"}) < '$pod_start'))'
    for i in $(seq 1 240); do
      v=$(vq "$q"); [ "${v:-0}" -ge "$n" ] && tc=$(( $(date +%s) - pod_start )) && break; sleep 5
    done; pf_stop
    save "RESTART_SEEN_COLLECTOR_$t" "${tc:-none}"; log "after a restart the collector had the full inventory after ${tc:-none} s (pod $pod)"
    oc get pod -n "$ns" "$pod" -o jsonpath='{.status.containerStatuses[0].restartCount} {.status.containerStatuses[0].lastState}' > "$dir/raw/$t-restart-collector-state.txt" 2>/dev/null
    sleep $((settle * 60)); end=$(date +%s); save "RESTART_END_$t" "$end"
    export_run "$t restart: collector pod recreated" steady "$start" "$end" "pod start=$pod_start"
    pull_audit "$t-restart" "$start" "$end" ;;
  restart-ksm)
    need_units; t=$(tag); start=$(date +%s); save "RESTART_KSM_START_$t" "$start"
    # the kube_* series carry no instance or pod label (CMO relabeling), so the new pod is recognised through the sample count
    # of its scrape target: the inventory is served when the new target returns at least 95 % of the samples of the old one
    qb='max(scrape_samples_scraped{job="kube-state-metrics",container="kube-rbac-proxy-main"})'; before=$(tq "$qb"); threshold=$(( before * 95 / 100 ))
    oc delete pod -n openshift-monitoring -l app.kubernetes.io/name=kube-state-metrics --wait=false >/dev/null
    sleep 5; oc rollout status deploy/kube-state-metrics -n openshift-monitoring --timeout=10m >/dev/null
    pod=$(oc get pods -n openshift-monitoring -l app.kubernetes.io/name=kube-state-metrics -o jsonpath='{.items[0].metadata.name}'); pod_start=$(pod_start_ts openshift-monitoring "$pod")
    ip=$(oc get pod -n openshift-monitoring "$pod" -o jsonpath='{.status.podIP}'); tk=""
    q='max(scrape_samples_scraped{job="kube-state-metrics",container="kube-rbac-proxy-main",instance="'$ip':8443"})'
    for i in $(seq 1 240); do
      v=$(tq "$q"); [ "${v:-0}" -ge "$threshold" ] && tk=$(( $(date +%s) - pod_start )) && break; sleep 5
    done
    now=$(date +%s); tk2=$(first_reach thanos "$q" "$threshold" "$pod_start" "$now"); tk=${tk2:-${tk:-none}}
    save "RESTART_SEEN_KSM_$t" "${tk:-none}"; save "RESTART_KSM_SAMPLES_BEFORE_$t" "$before"
    log "after a restart kube-state-metrics served the full inventory after ${tk:-none} s (pod $pod; first scrape with at least $threshold of $before samples, 60 s scrape interval)"
    sleep $((settle * 60)); end=$(date +%s); save "RESTART_KSM_END_$t" "$end"
    export_run "$t restart-ksm: kube-state-metrics pod recreated" steady "$start" "$end" "pod start=$pod_start"
    pull_audit "$t-restart-ksm" "$start" "$end" ;;
  restart-ksm-finish)  # finishes an interrupted restart-ksm phase: the pod is already recreated, the start is saved
    need_units; t=$(tag); start=$(eval echo "\$RESTART_KSM_START_$t")
    pod=$(oc get pods -n openshift-monitoring -l app.kubernetes.io/name=kube-state-metrics -o jsonpath='{.items[0].metadata.name}'); pod_start=$(pod_start_ts openshift-monitoring "$pod")
    ip=$(oc get pod -n openshift-monitoring "$pod" -o jsonpath='{.status.podIP}')
    qb='max(max_over_time(scrape_samples_scraped{job="kube-state-metrics",container="kube-rbac-proxy-main"}[10m] offset '$(( $(date +%s) - start + 60 ))'s))'; before=$(tq "$qb"); threshold=$(( before * 95 / 100 ))
    q='max(scrape_samples_scraped{job="kube-state-metrics",container="kube-rbac-proxy-main",instance="'$ip':8443"})'
    now=$(date +%s); tk=$(first_reach thanos "$q" "$threshold" "$pod_start" "$now")
    save "RESTART_SEEN_KSM_$t" "${tk:-none}"; save "RESTART_KSM_SAMPLES_BEFORE_$t" "$before"
    log "after a restart kube-state-metrics served the full inventory after ${tk:-none} s (pod $pod; first scrape with at least $threshold of $before samples, 60 s scrape interval)"
    remaining=$(( pod_start + settle * 60 - now )); [ "$remaining" -gt 0 ] && sleep "$remaining"
    end=$(date +%s); save "RESTART_KSM_END_$t" "$end"
    export_run "$t restart-ksm: kube-state-metrics pod recreated" steady "$start" "$end" "pod start=$pod_start"
    pull_audit "$t-restart-ksm" "$start" "$end" ;;
  churn)
    need_units; t=$(tag); slice=$(( units / 10 )); [ "$slice" -ge 1 ] || slice=1
    start=$(date +%s); save "CHURN_START_$t" "$start"
    summary=$(loader_job "$t-churn-delete" delete --from 0 --to "$slice" --kind deployments); log "loader delete: $summary"
    deleted=$(date +%s); sleep 60
    summary=$(loader_job "$t-churn-recreate" recreate --from 0 --to "$slice" --kind deployments --workers "$workers"); log "loader recreate: $summary"
    recreated=$(date +%s); save "CHURN_SLICE_$t" "$slice"
    log "churn: the deployments of $slice namespace(s) ($(( slice * DEP_PER_UNIT ))) deleted and recreated"
    sleep $(( 7 * 60 ))
    end=$(date +%s); save "CHURN_END_$t" "$end"; m="delete=$start;deleted=$deleted;recreated=$recreated"; save "CHURN_MARKERS_$t" "$m"
    export_run "$t churn: deployments of $slice namespaces recreated" steady "$start" "$end" "$m"
    pull_audit "$t-churn" "$start" "$end" ;;
  steady2)
    need_units; t=$(tag); start=$(date +%s); save "STEADY2_START_$t" "$start"; sleep $(( 10 * 60 )); end=$(date +%s); save "STEADY2_END_$t" "$end"
    export_run "$t steady2: after the churn" steady "$start" "$end"; cp_snapshot "$t-steady2" || true ;;
  step)
    need_units
    for p in create steady restart restart-ksm churn steady2; do
      "$0" "$dir" "$p" "$units" || { rc=$?; log "phase $p of step ${units}k failed ($rc)"; exit $rc; }
    done ;;
  audit-repull)  # <tag>: re-pulls the audit events of a saved window (e.g. 10k-restart) after a change of the filter
    [ -n "$units" ] || { echo "audit-repull needs the tag"; exit 1; }; t=$units; units=""
    step=${t%%-*}; k=$(echo "${t#*-}" | tr 'a-z-' 'A-Z_'); start=$(eval echo "\${${k}_START_${step}:-}"); end=$(eval echo "\${${k}_END_${step}:-}")
    [ -n "$start" ] && [ -n "$end" ] || { echo "no window for $t ($k)"; exit 1; }
    pull_audit "$t" "$start" "$end" ;;
  timeline)
    . "$state"; m=""
    for v in $(grep -oE '^(CREATE_START|CREATE_END|RESTART_START|RESTART_KSM_START|CHURN_START)_[0-9]+k' "$state" | sort -u); do
      m="${m:+$m;}$(echo "$v" | sed -E 's/_([0-9]+k)$/ \1/; s/CREATE_START/loader start/; s/CREATE_END/loader end/; s/RESTART_KSM_START/ksm restart/; s/RESTART_START/restart/; s/CHURN_START/churn/' | tr 'A-Z' 'a-z')=$(eval echo "\$$v")"
    done
    units=0; STEP=60 export_run "timeline: whole ladder" timeline "$BASELINE_START" "$(date +%s)" "$m" ;;
  cleanup)
    done_units=${UNITS_DONE:-0}
    summary=$(loader_job "cleanup" cleanup --from 0 --to "$done_units"); log "loader cleanup: $summary"
    oc delete -f load/loader-driver.yaml --wait=false >/dev/null 2>&1
    oc delete -f 08-k8scluster-collector.yaml >/dev/null 2>&1
    log "inventory namespaces (0-$done_units), cluster resource quotas, loader driver and the k8s_cluster-only collector deleted" ;;
  *) echo "unknown phase $phase"; exit 1 ;;
esac
log "phase $phase done"
