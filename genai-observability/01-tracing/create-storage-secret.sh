#!/usr/bin/env bash
# Creates the Secret tempo-storage with a random S3 secret key. SeaweedFS (01-tracing/seaweedfs.yaml) and the
# TempoStack (01-tracing/tempostack.yaml) read it. Nothing is created if the Secret already exists.
set -euo pipefail
NS="${NAMESPACE:-genai-demo}"
if oc get secret tempo-storage -n "$NS" >/dev/null 2>&1; then
  echo "Secret tempo-storage already exists in $NS"
  exit 0
fi
oc create namespace "$NS" 2>/dev/null || true
oc create secret generic tempo-storage -n "$NS" \
  --from-literal=endpoint="http://seaweedfs.${NS}.svc.cluster.local:8333" \
  --from-literal=bucket=tempo \
  --from-literal=access_key_id=tempo \
  --from-literal=access_key_secret="$(openssl rand -hex 16)"
