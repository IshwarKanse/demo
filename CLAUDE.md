# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains demo resources and [Chainsaw](https://kyverno.github.io/chainsaw/) end-to-end tests for OpenShift observability and AI components, used for presentations. Chainsaw is a Kubernetes testing tool that applies manifests and asserts expected cluster state. Tests run against a live OpenShift cluster (requires `oc` CLI authenticated).

## Prerequisites

- **chainsaw** >= v0.2.12
- **oc** (OpenShift CLI, authenticated to a cluster)
- **jq** (used in shell scripts for JSON parsing)

## Running Tests

Run all tests from the repo root (the root `.chainsaw.yaml` provides default timeouts):
```bash
chainsaw test --skip-delete <test-directory>
```

### Lightspeed tests
Uses its own `.chainsaw.yaml` config with longer timeouts and parallelism. Requires provider credentials:
```bash
chainsaw test --config ./lightspeed/.chainsaw.yaml --skip-delete ./lightspeed --values - <<EOF
LIGHTSPEED_PROVIDER_URL: "https://api.openai.com/v1"
LIGHTSPEED_PROVIDER_TOKEN: "<token>"
EOF
```
When invoked from Cypress, environment variables `CYPRESS_LIGHTSPEED_PROVIDER_URL` and `CYPRESS_LIGHTSPEED_PROVIDER_TOKEN` are used (Cypress strips the `CYPRESS_` prefix).

### Tempo RBAC tests
```bash
chainsaw test --skip-delete tempo
```

## Repository Structure

- **`operators/`** - OLM Subscription manifests to install Cluster Observability Operator (COO) and Lightspeed Operator on OpenShift.
- **`lightspeed/`** - Chainsaw test that deploys OpenShift Lightspeed OLSConfig and its API credential secret. Has its own `.chainsaw.yaml` config with custom timeouts/parallelism.
- **`tempo/multitenancy-rbac/`** - Multi-step Chainsaw test for Tempo multitenancy RBAC: installs MinIO storage, TempoStack, OpenTelemetry collector, generates traces via HotROD app, creates non-admin ServiceAccounts with namespace-scoped access, and verifies trace visibility and span metrics.
- **`observabilityinstaller/`** - Manifests for the ObservabilityInstaller CR (tracing capability), MinIO object storage, and a HotROD trace-generating app. Used with Cluster Observability Operator.
- **`online-boutique/`** - Kustomize overlay that deploys [Google Online Boutique](https://github.com/GoogleCloudPlatform/microservices-demo) (11 microservices) as a trace-generating demo app. Pulls upstream manifests directly via remote resource; patches configure OTel tracing to the local collector and strip `securityContext` for OpenShift SCC compatibility. Deploy/delete with `oc apply -k online-boutique/` / `oc delete -k online-boutique/`.
- **`apm-dashboard/`** - UIPlugin manifest enabling Perses-based monitoring dashboards.
- **`otel-ocp-metrics-export/`** - Proof of concept resources (`poc/`) and sizing benchmark for exporting the OpenShift monitoring metrics through the OpenTelemetry Collector with Prometheus remote write v2: manifests (OTLP sink, collector under test, monitoring config maps, avalanche load generator) and scripts (`run-benchmark.sh`, `collect.sh`, `outage-test.sh`, `pq.sh`) that query Thanos Querier; results and the resource recommendation in its README. Needs OpenShift 5.0+ and the OpenTelemetry operator, no credentials.
- **`genai-observability/`** - GenAI observability demo: vLLM (CPU) behind OGX (Llama Stack), a chat client with the OpenTelemetry GenAI instrumentation, one OpenTelemetryCollector, a multi-tenant TempoStack (SeaweedFS storage, traces in Observe > Traces through the Cluster Observability Operator tracing UI plugin) and the "OpenTelemetry GenAI" console dashboard (published by the OpenTelemetry operator, branch `genai-dashboard` of the user's operator fork; `dashboard/` has a copy and a loader script). Numbered directories `00-cluster` to `07-verify` with a top-level `chainsaw-test.yaml`; run with `chainsaw test --skip-delete genai-observability`. Needs OpenShift 4.20+, a worker with 16 vCPU and 32 GiB, no GPU. See its README.
- **`.chainsaw.yaml`** (root) - Default Chainsaw configuration with 5-minute timeouts for assert/cleanup/delete/error/exec.

## Test Pattern

Each Chainsaw test directory follows the pattern:
1. `chainsaw-test.yaml` - Test definition with ordered steps (apply + assert pairs)
2. Resource manifests (e.g., `00-install-storage.yaml`) - Kubernetes resources to apply
3. Assert manifests (e.g., `00-assert.yaml`, `assert-*.yaml`) - Expected state to verify
4. Optional shell scripts (e.g., `check_metrics.sh`) for validation that requires API calls

The `--skip-delete` flag is typically used to preserve resources after test runs for debugging.
