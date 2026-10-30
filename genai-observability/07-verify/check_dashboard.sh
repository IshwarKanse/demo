#!/usr/bin/env bash
# The OpenTelemetry operator publishes the GenAI dashboard as a labelled ConfigMap.
set -eu
cm=opentelemetry-genai
label=$(oc get cm "$cm" -n openshift-config-managed -o jsonpath='{.metadata.labels.console\.openshift\.io/dashboard}')
title=$(oc get cm "$cm" -n openshift-config-managed -o json | jq -r '.data | to_entries[0].value | fromjson | .title')
[ "$label" = "true" ] || { echo "FAIL: label console.openshift.io/dashboard is '$label'"; exit 1; }
[ "$title" = "OpenTelemetry GenAI" ] || { echo "FAIL: dashboard title is '$title'"; exit 1; }
echo "OK: ConfigMap $cm, dashboard '$title'"
