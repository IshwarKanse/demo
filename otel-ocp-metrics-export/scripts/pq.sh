#!/bin/bash
# Instant PromQL query against the cluster's Thanos Querier.
# usage: scripts/pq.sh '<promql>'   (KUBECONFIG must point at the cluster)
set -euo pipefail
query=$1
TOKEN=$(oc create token prometheus-k8s -n openshift-monitoring)
HOST=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')
curl -sk -H "Authorization: Bearer $TOKEN" "https://$HOST/api/v1/query" --data-urlencode "query=$query" \
  | jq -r '.data.result[] | "\(.metric | del(.__name__) | tojson) => \(.value[1])"'
