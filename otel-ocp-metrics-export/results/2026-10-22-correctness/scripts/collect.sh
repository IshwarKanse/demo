#!/bin/bash
# Collect the raw material of one run: the source samples of the senders (instant queries with a
# range selector return the raw samples with their real timestamps), the sender and collector
# counters at the window boundaries, exemplars and metadata of the typed sender, the sink's
# per-series and per-family sample counts, and the file exporter dumps of the three collectors.
# Everything is written under <outdir>/raw/. The Prometheus APIs are reached with oc port-forward.
# usage: scripts/collect.sh <outdir> <w1 start> <w1 end> <w2 start> <w2 end>   (epoch seconds)
set -uo pipefail
cd "$(dirname "$0")/.."; scripts=$(cd "$(dirname "$0")" && pwd)
out=$1; w1s=$2; w1e=$3; w2s=$4; w2e=$5; ns=otel-correctness; raw="$out/raw"; mkdir -p "$raw"
DUMP_RE='^(up|scrape_samples_scraped|node_cpu_seconds(_total)?|node_memory_MemAvailable_bytes|node_network_receive_bytes(_total)?|etcd_disk_wal_fsync_duration_seconds(_bucket|_sum|_count)?|prometheus_tsdb_head_series|prometheus_remote_storage_(samples|histograms|exemplars)_.*|kube_node_status_condition|kubelet_running_pods|go_gc_duration_seconds(_sum|_count)?|container_cpu_usage_seconds(_total)?|ALERTS|target_info)$'
pids=()
pf() { oc port-forward -n "$1" "$2" "$3:$4" >/dev/null 2>&1 & pids+=($!); }
cleanup() { for p in "${pids[@]}"; do kill "$p" 2>/dev/null; done; }
trap cleanup EXIT
pf $ns svc/typed-prometheus 19090 9090
pf $ns svc/sink-prometheus 19091 9090
pf openshift-monitoring pod/prometheus-k8s-0 19092 9090
pf openshift-monitoring pod/prometheus-k8s-1 19093 9090
sleep 4
q() { # q <port> <file> <query> [time]
  local port=$1 file=$2 query=$3 t=${4:-}
  curl -s --max-time 600 "http://localhost:$port/api/v1/query" --data-urlencode "query=$query" ${t:+--data-urlencode "time=$t"} > "$raw/$file"
  echo "$file: $(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["status"], len(d.get("data",{}).get("result",[])), "results")' "$raw/$file" 2>&1)"
}
counters='prometheus_remote_storage_samples_total|prometheus_remote_storage_samples_failed_total|prometheus_remote_storage_samples_dropped_total|prometheus_remote_storage_samples_retried_total|prometheus_remote_storage_samples_pending|prometheus_remote_storage_histograms_total|prometheus_remote_storage_histograms_failed_total|prometheus_remote_storage_histograms_dropped_total|prometheus_remote_storage_histograms_retried_total|prometheus_remote_storage_histograms_pending|prometheus_remote_storage_exemplars_total|prometheus_remote_storage_exemplars_failed_total|prometheus_remote_storage_exemplars_dropped_total|prometheus_remote_storage_metadata_total|prometheus_remote_storage_sent_batch_duration_seconds_count|prometheus_remote_storage_shards|prometheus_tsdb_head_series|prometheus_tsdb_head_samples_appended_total|prometheus_tsdb_out_of_order_samples_appended_total'
otelcounters='otelcol_receiver_accepted_metric_points|otelcol_receiver_refused_metric_points|otelcol_exporter_sent_metric_points|otelcol_exporter_send_failed_metric_points|otelcol_exporter_enqueue_failed_metric_points|otelcol_exporter_queue_size|otelcol_processor_refused_metric_points|otelcol_processor_dropped_metric_points|otelcol_process_memory_rss|otelcol_process_uptime'
for w in 1 2; do
  s=$(eval echo \$w${w}s); e=$(eval echo \$w${w}e); len=$((e - s))
  # typed sender: every raw sample of the window, counters at both boundaries
  q 19090 typed-source-w$w.json "{__name__=~\".+\"}[${len}s]" "$e"
  q 19090 typed-counters-w${w}-start.json "{__name__=~\"$counters\"}" "$s"
  q 19090 typed-counters-w${w}-end.json "{__name__=~\"$counters\"}" "$e"
  q 19090 otelcol-counters-w${w}-start.json "{__name__=~\"$otelcounters\"}" "$s"
  q 19090 otelcol-counters-w${w}-end.json "{__name__=~\"$otelcounters\"}" "$e"
  # otelcol counters as raw series (15 s resolution) to see the in-flight skew at the boundaries
  q 19090 otelcol-counters-w${w}-raw.json "{__name__=~\"otelcol_receiver_accepted_metric_points|otelcol_exporter_sent_metric_points|otelcol_exporter_queue_size\"}[${len}s]" "$e"
  # platform replicas: raw samples of the dumped families, counters at both boundaries, totals per family
  for r in 0 1; do p=$((19092 + r))
    q $p prod${r}-source-w$w.json "{__name__=~\"$DUMP_RE\"}[${len}s]" "$e"
    q $p prod${r}-counters-w${w}-start.json "{__name__=~\"$counters\"}" "$s"
    q $p prod${r}-counters-w${w}-end.json "{__name__=~\"$counters\"}" "$e"
    python3 "$scripts/family-counts.py" $p "$raw/prod${r}-family-counts-w$w.json" "$len" "$e"
  done
  # sink: per-series counts of the dumped families and per-family totals, split by sender replica
  python3 "$scripts/family-counts.py" 19091 "$raw/sink-family-counts-w$w.json" "$len" "$e" 'prometheus_replica=~"prometheus-k8s-.*"' prometheus_replica
  python3 "$scripts/family-counts.py" 19091 "$raw/sink-typed-family-counts-w$w.json" "$len" "$e" 'job=~"prometheus|avalanche|exemplar-app|stale-app|otelcol"' job
  python3 "$scripts/family-counts.py" 19090 "$raw/typed-family-counts-w$w.json" "$len" "$e" '' job
done
# exemplars and metadata of the typed sender over the whole run
curl -s "http://localhost:19090/api/v1/query_exemplars" --data-urlencode 'query={__name__=~"corr_.*|avalanche_.*"}' --data-urlencode "start=$w1s" --data-urlencode "end=$w2e" > "$raw/typed-source-exemplars.json"
curl -s "http://localhost:19090/api/v1/metadata" > "$raw/typed-source-metadata.json"
curl -s "http://localhost:19091/api/v1/query_exemplars" --data-urlencode 'query={__name__=~"corr_.*"}' --data-urlencode "start=$w1s" --data-urlencode "end=$w2e" > "$raw/sink-exemplars.json"
curl -s "http://localhost:19091/api/v1/metadata" > "$raw/sink-metadata.json"
curl -s "http://localhost:19090/api/v1/targets" > "$raw/typed-targets.json"
curl -s "http://localhost:19090/api/v1/status/buildinfo" > "$raw/typed-buildinfo.json"
curl -s "http://localhost:19092/api/v1/status/buildinfo" > "$raw/prod0-buildinfo.json"
# the platform Prometheus remote write configuration as rendered by the Cluster Monitoring Operator
oc get prometheus k8s -n openshift-monitoring -o jsonpath='{.spec.remoteWrite}' > "$raw/prod-remotewrite-spec.json"
# collector logs and file exporter dumps
for c in prod prod-contrib typed; do
  oc logs -n $ns deploy/$c-collector -c otc-container > "$raw/$c-collector.log" 2>&1
  pod=$(oc get pods -n $ns -l app.kubernetes.io/instance=$ns.$c -o jsonpath='{.items[0].metadata.name}')
  # ubi-minimal has neither tar (oc cp) nor gzip: stream the file with cat and retry until the
  # local size matches the size in the pod (the API server exec stream can reset on large transfers)
  want=$(oc exec -n $ns -c dumper "$pod" -- stat -c %s /data/export.jsonl)
  for try in 1 2 3 4 5; do
    oc exec -n $ns -c dumper "$pod" -- head -c "$want" /data/export.jsonl > "$raw/$c-dump.jsonl" 2>/dev/null
    have=$(stat -f %z "$raw/$c-dump.jsonl" 2>/dev/null || stat -c %s "$raw/$c-dump.jsonl")
    [ "$have" = "$want" ] && break; echo "$c dump transfer $have of $want bytes, retrying"; sleep 5
  done
  ls -la "$raw/$c-dump.jsonl"
done
oc logs -n $ns deploy/typed-prometheus > "$raw/typed-prometheus.log" 2>&1
oc get pods -n $ns -o wide > "$raw/pods.txt"
echo "windows $w1s $w1e $w2s $w2e" > "$raw/windows.txt"
