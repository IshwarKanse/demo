# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains [Chainsaw](https://kyverno.github.io/chainsaw/) end-to-end tests for OpenShift observability and AI components. Chainsaw is a Kubernetes testing tool that applies manifests and asserts expected cluster state. Tests run against a live OpenShift cluster (requires `oc` CLI authenticated).

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
- **`apm-dashboard/`** - UIPlugin manifest enabling Perses-based monitoring dashboards.
- **`.chainsaw.yaml`** (root) - Default Chainsaw configuration with 5-minute timeouts for assert/cleanup/delete/error/exec.

## Test Pattern

Each Chainsaw test directory follows the pattern:
1. `chainsaw-test.yaml` - Test definition with ordered steps (apply + assert pairs)
2. Resource manifests (e.g., `00-install-storage.yaml`) - Kubernetes resources to apply
3. Assert manifests (e.g., `00-assert.yaml`, `assert-*.yaml`) - Expected state to verify
4. Optional shell scripts (e.g., `check_metrics.sh`) for validation that requires API calls

The `--skip-delete` flag is typically used to preserve resources after test runs for debugging.
