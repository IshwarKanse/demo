#!/usr/bin/env bash
# Every metric family used by the GenAI dashboard must have at least one series in Thanos Querier.
set -u
NAMESPACE="${NAMESPACE:-genai-demo}"
oc create serviceaccount genai-metrics-reader -n "$NAMESPACE" 2>/dev/null || true
oc adm policy add-cluster-role-to-user cluster-monitoring-view "system:serviceaccount:${NAMESPACE}:genai-metrics-reader" >/dev/null
TOKEN=$(oc create token genai-metrics-reader -n "$NAMESPACE")
HOST=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')

queries=(
  'traces_span_metrics_calls_total{gen_ai_operation_name="chat"}'
  '{__name__=~"gen_ai_client_.*"}'
  '{__name__=~"ogx_inference.*"}'
  'vllm:generation_tokens_total'
  'vllm:kv_cache_usage_perc'
  'otelcol_receiver_accepted_spans'
)
rc=0
for q in "${queries[@]}"; do
  found=0
  for _ in $(seq 1 60); do
    n=$(curl -sk -H "Authorization: Bearer $TOKEN" -G --data-urlencode "query=$q" "https://$HOST/api/v1/query" | jq -r '.data.result | length' 2>/dev/null)
    if [ "${n:-0}" -ge 1 ]; then echo "OK   $q ($n series)"; found=1; break; fi
    sleep 10
  done
  [ "$found" = 1 ] || { echo "MISSING $q"; rc=1; }
done
exit $rc
