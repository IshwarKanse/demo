#!/bin/bash
# Instant PromQL query against the cluster's Thanos Querier.
# usage: scripts/pq.sh '<promql>'   (KUBECONFIG must point at the cluster)
set -euo pipefail
query=$1
# Thanos Querier access: a token that expires with the run, and the cluster's ingress CA to verify
# the route certificate (no -k).
TOKEN=$(oc create token prometheus-k8s -n openshift-monitoring --duration=30m)
HOST=$(oc get route thanos-querier -n openshift-monitoring -o jsonpath='{.spec.host}')
CA=$(mktemp)
trap 'rm -f "$CA"' EXIT
oc get configmap default-ingress-cert -n openshift-config-managed -o jsonpath='{.data.ca-bundle\.crt}' > "$CA"
[ -s "$CA" ] || { echo "could not read the ingress CA bundle (openshift-config-managed/default-ingress-cert)"; exit 1; }
curl -s --cacert "$CA" -H "Authorization: Bearer $TOKEN" "https://$HOST/api/v1/query" --data-urlencode "query=$query" \
  | jq -r '.data.result[] | "\(.metric | del(.__name__) | tojson) => \(.value[1])"'
