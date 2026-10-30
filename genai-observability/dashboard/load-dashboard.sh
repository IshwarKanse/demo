#!/usr/bin/env bash
# Publishes the "OpenTelemetry GenAI" dashboard to the OpenShift console without the operator build that embeds it.
# The console lists every ConfigMap in openshift-config-managed that has the label console.openshift.io/dashboard=true.
# A copy of this file is embedded in the OpenTelemetry operator branch genai-dashboard
# (internal/openshift/dashboards/genai-dashboard.json); keep both in sync.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
oc create configmap opentelemetry-genai -n openshift-config-managed \
  --from-file=genai.json="${here}/genai-dashboard.json" --dry-run=client -o yaml \
  | oc label --local -f - console.openshift.io/dashboard=true -o yaml \
  | oc apply -f -
echo "Open: Observe > Dashboards > OpenTelemetry GenAI (use Project: All Projects)"
