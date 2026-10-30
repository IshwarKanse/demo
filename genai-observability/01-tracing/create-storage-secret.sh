#!/usr/bin/env bash
# Creates the Secret tempo-storage with a random S3 secret key. SeaweedFS (01-tracing/seaweedfs.yaml) and the
# TempoStack (01-tracing/tempostack.yaml) read it.
# An existing Secret is kept, unless its key is empty or the well-known value from the first version of this demo
# ("supersecret"), which is public in the git history: that Secret is replaced. After a replacement, restart
# SeaweedFS and the Tempo pods so that they read the new key.
set -euo pipefail
NS="${NAMESPACE:-genai-demo}"

if oc get secret tempo-storage -n "$NS" >/dev/null 2>&1; then
  current=$(oc get secret tempo-storage -n "$NS" -o jsonpath='{.data.access_key_secret}' | base64 -d 2>/dev/null || true)
  if [ -n "$current" ] && [ "$current" != "supersecret" ]; then
    echo "Secret tempo-storage already exists in $NS"
    exit 0
  fi
  echo "Replacing the empty or well-known key in Secret tempo-storage ($NS)."
  echo "Restart SeaweedFS and the Tempo pods afterwards: oc rollout restart deploy/seaweedfs -n $NS"
  oc delete secret tempo-storage -n "$NS"
fi

oc create namespace "$NS" 2>/dev/null || true

# generate the key first so that a failure stops the script instead of creating an empty credential
key=$(openssl rand -hex 16)
if [ "${#key}" -lt 32 ]; then
  echo "failed to generate the S3 secret key" >&2
  exit 1
fi

# the key goes through stdin, not through the command line (visible to other users in the process list)
printf '%s' "$key" | oc create secret generic tempo-storage -n "$NS" \
  --from-literal=endpoint="http://seaweedfs.${NS}.svc.cluster.local:8333" \
  --from-literal=bucket=tempo \
  --from-literal=access_key_id=tempo \
  --from-file=access_key_secret=/dev/stdin
