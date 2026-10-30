# demo

Demo resources and Chainsaw end-to-end tests for OpenShift observability and AI components, used for presentations.

## Prerequisites

- [chainsaw](https://kyverno.github.io/chainsaw/latest/quick-start/install/) >= v0.2.12
- `oc` CLI (authenticated to an OpenShift cluster)
- `jq`

## Contents

| Directory | Description |
|---|---|
| `operators/` | OLM Subscriptions to install Cluster Observability Operator (COO) and Lightspeed Operator |
| `lightspeed/` | Chainsaw test for deploying OpenShift Lightspeed (OLSConfig + API credentials) |
| `tempo/` | Chainsaw test for Tempo multitenancy RBAC (storage, TempoStack, OTel collector, trace generation, RBAC verification) |
| `observabilityinstaller/` | Manifests for ObservabilityInstaller CR, MinIO object storage, and HotROD trace-generating app |
| `online-boutique/` | Kustomize overlay for [Google Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) — 11-microservice demo app for trace generation |
| `apm-dashboard/` | UIPlugin manifest enabling Perses-based monitoring dashboards |
| `otel-ocp-metrics-export/` | Proof of concept resources (`poc/`), sizing benchmark manifests and scripts, measured results and the resource recommendation for exporting the OpenShift monitoring metrics through the OpenTelemetry Collector with Prometheus remote write v2 |
| `genai-observability/` | GenAI observability on OpenShift: vLLM on CPU behind OGX (Llama Stack), traced and measured with the OpenTelemetry operator and collector, a multi-tenant TempoStack (Observe > Traces) and a console dashboard; manifests, a Chainsaw test and verification scripts |

## Online Boutique Demo App

Deploy the [Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) microservices app, configured to export traces to the tracing stack's OTel collector:
```bash
oc apply -k online-boutique/
```

Delete:
```bash
oc delete -k online-boutique/
```

## Running Tests

### Tempo RBAC
```bash
chainsaw test --skip-delete tempo
```

### Lightspeed
Requires provider credentials — see [lightspeed/README.md](lightspeed/README.md) for details.
```bash
chainsaw test --config ./lightspeed/.chainsaw.yaml --skip-delete ./lightspeed --values - <<EOF
LIGHTSPEED_PROVIDER_URL: "https://api.openai.com/v1"
LIGHTSPEED_PROVIDER_TOKEN: "<your-token>"
EOF
```

