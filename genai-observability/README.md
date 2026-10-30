# GenAI observability on OpenShift

A complete, small LLM stack observed with OpenTelemetry on OpenShift, using the OpenTelemetry operator directly
(the Cluster Observability Operator is not part of the data path):

- **vLLM** serves `Qwen2.5-1.5B-Instruct` on CPU, so no GPU is needed.
- **OGX** (the upstream project formerly called Llama Stack) sits in front of vLLM and exposes the OpenAI-compatible API.
- A **chat client** instrumented with the OpenTelemetry GenAI instrumentation calls OGX.
- One **OpenTelemetryCollector** receives traces, metrics and logs from all three, derives request metrics from the spans and exports traces to **Tempo** and metrics to **user workload monitoring**.
- A new **"OpenTelemetry GenAI" dashboard** in **Observe > Dashboards** shows requests, tokens, latency, errors, the Llama Stack server and the vLLM engine.
  The dashboard is shipped by the OpenTelemetry operator itself, the same way the existing "OpenTelemetry Collector" dashboard is.

Contents: [Architecture](#architecture) · [Repository layout](#repository-layout) · [Prerequisites and sizing](#prerequisites-and-sizing) ·
[Install](#install) · [What each piece does](#what-each-piece-does) · [The dashboard](#the-dashboard) · [Verify](#verify) ·
[Demo script](#demo-script) · [Troubleshooting](#troubleshooting) · [Variations](#variations) · [Cleanup](#cleanup) · [Status and limitations](#status-and-limitations)

## Architecture

```mermaid
flowchart LR
  subgraph ns["namespace genai-demo"]
    C["chat-client<br/>OpenAI SDK + GenAI instrumentation"]
    L["loadgen Job"]
    O["OGX server<br/>starter distribution"]
    V["vLLM on CPU<br/>Qwen2.5-1.5B-Instruct"]
    COL["OpenTelemetryCollector genai"]
    T[("TempoMonolithic genai")]
    C -->|"chat completions /v1"| O
    L --> O
    L --> V
    O -->|"OpenAI-compatible API"| V
    C -->|"OTLP http 4318"| COL
    O -->|"OTLP http 4318"| COL
    V -->|"OTLP grpc 4317 (traces)"| COL
    COL -->|"scrape /metrics every 10s"| V
    COL -->|"OTLP 4317"| T
  end
  COL -->|"prometheus exporter :8889<br/>ServiceMonitor"| UWM["User workload Prometheus"]
  O -->|"/metrics :9464<br/>ServiceMonitor"| UWM
  UWM --> TQ["Thanos Querier"]
  TQ --> D["Console dashboard<br/>OpenTelemetry GenAI"]
  T --> J["Jaeger UI route"]
  OP["OpenTelemetry operator"] -.->|"publishes ConfigMap<br/>opentelemetry-genai"| D
```

A request takes this path: the client calls OGX, OGX calls vLLM. The OpenAI SDK uses httpx, and the httpx instrumentation
adds the W3C `traceparent` header, so the client, OGX and vLLM spans end up in **one trace**.

| Signal | Produced by | Path to the dashboard |
|---|---|---|
| Traces | client (GenAI spans), OGX (FastAPI and provider spans), vLLM (`llm_request` span with latency breakdown) | collector, then Tempo (Jaeger UI) |
| Request metrics (RED) | derived in the collector from the spans by the `span_metrics` connector, with `gen_ai.request.model`, `gen_ai.operation.name` and `gen_ai.provider.name` as extra dimensions | collector Prometheus exporter, then user workload monitoring |
| GenAI client metrics | the client instrumentation: `gen_ai.client.token.usage`, `gen_ai.client.operation.duration`, time to first chunk, time per output chunk | OTLP, collector, Prometheus exporter |
| Llama Stack server metrics | OGX: `ogx_inference_*`, `ogx_concurrent_requests`, `ogx_requests_total` | scraped from OGX `/metrics` through the ServiceMonitor the OGX operator creates |
| vLLM engine metrics | vLLM `/metrics`: tokens, TTFT, inter-token latency, KV cache, queue | scraped by the collector (`prometheus/vllm` receiver) |
| Collector health | the collector's own telemetry (`otelcol_*`) | ServiceMonitor created by the OpenTelemetry operator |
| Logs | prompt and completion log events (`gen_ai.user.message`, `gen_ai.choice`) | collector logs pipeline, `debug` exporter only (no log store in this demo) |

## Repository layout

```
genai-observability/
  README.md
  chainsaw-test.yaml          whole demo as a Chainsaw test
  dashboard/
    genai-dashboard.json      the console dashboard (copy of the file embedded in the operator branch)
    load-dashboard.sh         publishes the dashboard without the custom operator build
  00-cluster/                 namespace, user workload monitoring, Tempo operator subscription
  01-tracing/                 TempoMonolithic (+ optional Observe > Traces console plugin)
  02-collector/               OpenTelemetryCollector and the RBAC for k8sattributes
  03-inference/               vLLM Deployment, Service, PVC (+ optional SCC)
  04-ogx/                     OGXServer custom resource
  05-app/                     chat client (ConfigMap with the script + Deployment)
  06-load/                    load generator Job
  07-verify/                  trace check Job, metrics check script, dashboard check script
```

Every directory has `assert-*.yaml` files that Chainsaw uses to wait for readiness.

## Prerequisites and sizing

- OpenShift 4.20 or newer (verified on 5.0), cluster-admin, `oc`, optionally [chainsaw](https://kyverno.github.io/chainsaw/latest/quick-start/install/) >= v0.2.12 and `jq`.
- A worker with **at least 16 vCPU and 32 GiB** for vLLM, with AVX-512 (any `m5`, `m6i`, `m7i` or newer instance). No GPU.
- Internet access from the cluster: Docker Hub (vLLM, OGX), Hugging Face (model, about 3 GB, not gated), PyPI (client packages), ghcr.io (collector image).

| Component | CPU request / limit | Memory request / limit | Storage |
|---|---|---|---|
| vLLM (`vllm/vllm-openai-cpu:v0.32.0-x86_64`) | 12 / 12 | 20Gi / 28Gi (about 21.6 GiB used in float32) | 20Gi PVC for the model cache, 4Gi memory-backed `/dev/shm` |
| OGX server (`ogxai/distribution-starter`, pinned by the OGX operator) | 1 / 2 | 2Gi / 4Gi | 5Gi PVC |
| OpenTelemetry collector (contrib 0.162.0) | 500m / 1 | 512Mi / 1Gi | none |
| Tempo monolithic | operator defaults | operator defaults | 10Gi PVC |
| chat client | 100m / 500m | 256Mi / 512Mi | none |
| load generator | 100m / 500m | 128Mi / 256Mi | none |
| **Total** | **about 14 vCPU** | **about 24 GiB** | **35 GiB** |

The demo was built and verified on OCP 5.0 on AWS with 3 control plane nodes (`m6i.xlarge`) and 4 workers (`m5.4xlarge`, 16 vCPU and 64 GiB each).
Only one worker is really needed for vLLM; the others host everything else.

## Install

### 1. The OpenTelemetry operator

The dashboard is embedded in the operator, so the demo needs an operator build that contains it.
The change is on the branch `genai-dashboard` of the fork [IshwarKanse/opentelemetry-operator](https://github.com/IshwarKanse/opentelemetry-operator/tree/genai-dashboard)
(on top of upstream `main`; not submitted upstream).
It adds `internal/openshift/dashboards/genai-dashboard.json`, publishes it as ConfigMap `opentelemetry-genai` next to the existing `opentelemetry-collector` one,
removes both on shutdown and has unit tests. The OpenShift bundle already sets `OPENSHIFT_CREATE_DASHBOARD=true`.

**Option A, build the fork** (what the demo used):

```bash
git clone https://github.com/IshwarKanse/opentelemetry-operator.git && cd opentelemetry-operator
git checkout genai-dashboard
export IMG=quay.io/<your-namespace>/opentelemetry-operator:genai
export BUNDLE_IMG=quay.io/<your-namespace>/opentelemetry-operator-bundle:genai

IMG=$IMG BUNDLE_VARIANT=openshift make bundle
IMG=$IMG BUNDLE_IMG=$BUNDLE_IMG BUNDLE_VARIANT=openshift \
  GOOS=linux GOARCH=amd64 ARCH=amd64 DOCKER_BUILDX_FLAGS="--platform=linux/amd64" \
  make container container-push bundle-build bundle-push

oc create namespace opentelemetry-operator-system
oc label namespace opentelemetry-operator-system openshift.io/cluster-monitoring=true
operator-sdk run bundle "$BUNDLE_IMG" --namespace opentelemetry-operator-system \
  --timeout 6m --security-context-config=restricted
```

Notes for building on Apple Silicon: the Makefile `docker build --load` lines need `${DOCKER_BUILDX_FLAGS}` added so that the `--platform=linux/amd64`
flag is passed, and `make bundle` rewrites tracked files. Do both in a throwaway worktree, not in your branch.
The quay.io repositories must be public (or the cluster needs a pull secret).
If you only change the dashboard JSON later, rebuild just the operator image, push a new tag and patch the CSV:
`oc patch csv <csv> -n opentelemetry-operator-system --type=json -p '[{"op":"replace","path":"/spec/install/spec/deployments/0/spec/template/spec/containers/0/image","value":"<new image>"}]'`.

**Option B, any other OpenTelemetry operator** (community catalog or the Red Hat build): everything works except that the operator does not publish the GenAI dashboard.
Load it yourself:

```bash
genai-observability/dashboard/load-dashboard.sh
```

### 2. Everything else

With Chainsaw (applies each directory in order and waits for readiness; allow 30 to 40 minutes on a fresh cluster, most of it is the model download and start):

```bash
chainsaw test --skip-delete genai-observability
```

Or by hand:

```bash
D=genai-observability

# cluster prerequisites: namespace, user workload monitoring, Tempo operator, OGX operator
oc apply -f $D/00-cluster/namespace.yaml -f $D/00-cluster/user-workload-monitoring.yaml -f $D/00-cluster/tempo-operator.yaml
oc apply -f https://raw.githubusercontent.com/ogx-ai/ogx-k8s-operator/v0.17.0/release/operator-openshift.yaml

# tracing and the collector
oc apply -f $D/01-tracing/tempo-monolithic.yaml
oc apply -f $D/02-collector/rbac.yaml -f $D/02-collector/otel-collector.yaml

# inference: start vLLM first and wait until it is ready (model download and load, 3 to 10 minutes)
oc apply -f $D/03-inference/vllm.yaml
oc rollout status deploy/vllm -n genai-demo --timeout=25m

# OGX registers the vLLM model when it starts, so deploy it after vLLM is ready
oc apply -f $D/04-ogx/ogxserver.yaml
oc apply -f $D/05-app/chat-client.yaml

# send one request and wait for it: the first request compiles CPU kernels (5 to 10 minutes), see Troubleshooting
oc apply -f $D/06-load/loadgen.yaml
```

`00-cluster/user-workload-monitoring.yaml` is a cluster-wide ConfigMap. On a cluster that already has a `cluster-monitoring-config`, merge `enableUserWorkload: true` into it instead of applying the file.

## What each piece does

### Collector (`02-collector/otel-collector.yaml`)

| Section | Configuration | Why |
|---|---|---|
| receivers | `otlp` (gRPC 4317, HTTP 4318); `prometheus/vllm` scraping `vllm.genai-demo.svc:8000` every 10 s | client, OGX and vLLM push OTLP; vLLM metrics are only available as a Prometheus endpoint |
| processors | `memory_limiter`, `k8sattributes`, `batch`, `transform/vllm-semconv` | see below |
| connector | `span_metrics` with histogram unit `s`, buckets 100 ms to 60 s, extra dimensions `gen_ai.request.model`, `gen_ai.operation.name`, `gen_ai.provider.name` | derives request rate, errors and latency per model from the traces |
| exporters | `otlp/tempo`, `prometheus` on `:8889` with `resource_to_telemetry_conversion`, `debug` | traces to Tempo, metrics to user workload monitoring |
| pipelines | traces: `otlp` to Tempo and `span_metrics`; metrics: `otlp`, `prometheus/vllm`, `span_metrics` to Prometheus; logs: `otlp` to `debug` | |

`transform/vllm-semconv` exists because vLLM spans use the pre-stable GenAI attribute names (`gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`)
and lack `gen_ai.request.model`, `gen_ai.operation.name` and `gen_ai.provider.name`. The processor copies them to the current semantic convention names
for spans that carry vLLM's `gen_ai.request.id`, so vLLM spans line up with the client spans.

`observability.metrics.enableMetrics: true` makes the operator create the ServiceMonitors for the collector's own metrics and for the Prometheus exporter.
The collector image is the upstream contrib one (`opentelemetry-collector-contrib:0.162.0`) because the community operator injects the core image by default, which lacks several of these components.
`resource_to_telemetry_conversion` is deprecated in contrib 0.162 and still works.

### vLLM (`03-inference/vllm.yaml`)

- Image `vllm/vllm-openai-cpu:v0.32.0-x86_64`, entrypoint `vllm serve`, model `Qwen/Qwen2.5-1.5B-Instruct`, served as `qwen2.5-1.5b`, `--max-model-len=4096`.
- `--enable-auto-tool-choice --tool-call-parser=hermes` so the client's tool-call requests work.
- `--otlp-traces-endpoint` plus `--collect-detailed-traces=all` export one span per request with the queue, prefill and decode timings.
- `--dtype=float32`: the `m5` and `m6i` CPUs have AVX-512 but no bfloat16 instructions, where bfloat16 is slow. On `m7i` or newer (AMX) use `--dtype=bfloat16`.
- `VLLM_CPU_KVCACHE_SPACE=8` (GiB of KV cache) and `VLLM_CPU_OMP_THREADS_BIND=0-10` (11 compute threads, one core left over; CPU request and limit are 12).
- `HOME`, `VLLM_CACHE_ROOT`, `VLLM_CONFIG_ROOT`, `XDG_CACHE_HOME` point to the PVC or `/tmp`, because the pod runs with a random UID under the default restricted SCC and has no writable home.
- `enableServiceLinks: false`, see Troubleshooting. The pod runs without a custom SCC; `vllm-scc.yaml` is only a fallback.

### OGX (`04-ogx/ogxserver.yaml`)

The OGX operator (v0.17.0, `ogx.io/v1beta1`) reconciles an `OGXServer`. The `starter` distribution activates its vLLM provider only because `VLLM_URL` is set.
Telemetry is configured with plain environment variables (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME=ogx-server`, `OTEL_METRIC_EXPORT_INTERVAL=5000`,
`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`). The old `telemetry:` provider and `TELEMETRY_SINKS` of Llama Stack 0.2 and 0.3 no longer exist; most blog posts still describe them.
The operator creates the Deployment `genai`, the Service `genai-service` (8321 for the API, 9464 for `/metrics`) and a ServiceMonitor.
The model is exposed as `vllm/qwen2.5-1.5b`.

### Chat client (`05-app/chat-client.yaml`)

A Python loop (script in a ConfigMap, packages installed at pod start) that sends a prompt every few seconds in three modes: plain chat, streaming chat and a tool-call request.
It uses the plain `openai` SDK against OGX and `opentelemetry-instrument` with:

- `opentelemetry-instrumentation-genai-openai` 1.3b0 (the older `opentelemetry-instrumentation-openai-v2` is deprecated) for the GenAI spans and metrics,
- `opentelemetry-instrumentation-httpx` so the trace context reaches OGX; without it the client traces stop at the client,
- `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_and_event` to record prompts and completions on the span and as log events.

The client selects the model by the `vllm/` prefix because OGX also lists static entries for providers without credentials.

### Load generator (`06-load/loadgen.yaml`)

A Job that runs for 600 s with two workers through OGX and one worker straight at vLLM, so that every dashboard row, including the vLLM engine row, moves.

## The dashboard

The dashboard uses the console's legacy dashboard format (Grafana 5 style JSON with `rows`).
The console renders only the panel types `graph`, `singlestat`, `gauge`, `table` and `grafana-piechart-panel`, so the JSON sticks to the first four.
Tables use instant queries whose label sets must be identical so that the console can merge them into rows.

Open it with **Observe > Dashboards**, dashboard **OpenTelemetry GenAI**, project **All Projects**
(direct link path: `/monitoring/dashboards/opentelemetry-genai?project-dropdown-value=%23ALL_NS%23`).
Variables: **Collector namespace**, **Service**, **Model**.

| Row | Panels (25 in total) | Main metrics |
|---|---|---|
| Overview | requests per second, error rate, P95 request latency, output tokens per second, KV cache usage (gauge), requests running | `traces_span_metrics_calls_total`, `traces_span_metrics_duration_seconds_bucket`, `vllm:generation_tokens_total`, `vllm:kv_cache_usage_perc`, `vllm:num_requests_running` |
| GenAI client (semantic conventions) | requests per second by model and operation, token usage per second by model and type, request duration P50 and P95, time to first chunk, time per output chunk, calls by service, table of models and services | `traces_span_metrics_*` with `gen_ai_*` dimensions, `gen_ai_client_token_usage`, `gen_ai_client_operation_time_to_first_chunk_seconds`, `gen_ai_client_operation_time_per_output_chunk_seconds` |
| Llama Stack (OGX) server | inference duration P95, time to first token P95, tokens per second per request, concurrent requests | `ogx_inference_duration_seconds`, `ogx_inference_time_to_first_token_seconds`, `ogx_inference_tokens_per_second`, `ogx_concurrent_requests` |
| vLLM engine | prompt and generation tokens per second, TTFT P50 and P95, end-to-end latency P50 and P95, inter-token latency P95, requests running and waiting, KV cache and prefix cache hit rate | `vllm:*` |
| OpenTelemetry collector | spans accepted, refused and failed per second, metric points accepted and refused per second | `otelcol_*` |

Things worth knowing:

- **Metric names drift.** The GenAI semantic conventions are still in development; newer versions rename the token metric to `gen_ai.client.inference.usage.*_tokens`.
  The token panels use `... or ...` so that either name works. The demo showed the older `gen_ai_client_token_usage` histogram with a `gen_ai_token_type` label.
- **Labels.** Dots become underscores in Prometheus (`gen_ai_request_model`, `service_name`). The `namespace` label is the namespace of the collector (added by the ServiceMonitor), `k8s_namespace_name` is the workload namespace.
- **A console quirk.** A dashboard variable called `namespace` is special-cased by the console (it follows the Project dropdown). On the OCP 5.0 build used here it rendered the literal text `ALL_OPTION_KEY` and every panel that uses it was empty,
  The existing "OpenTelemetry Collector" dashboard also showed "No datapoints found" on this cluster with `namespace=ALL_OPTION_KEY` in its URL; its other variables may contribute, so the cause there is not confirmed.
  The GenAI dashboard calls its variable `collector namespace` to avoid the problem.
  The console shows the variable name (title-cased) as the dropdown label, not the `label` field.
- **vLLM metric names** use colons (`vllm:kv_cache_usage_perc`). The old `vllm:gpu_cache_usage_perc` no longer exists.
- Cost per token and similar business metrics are not included.

How the operator publishes it: `internal/openshift/dashboards/dashboards.go` embeds `metrics-dashboard.json` and `genai-dashboard.json`,
creates or updates the ConfigMaps `opentelemetry-collector` and `opentelemetry-genai` in `openshift-config-managed` (label `console.openshift.io/dashboard=true`) when the operator starts
and deletes them when it stops. To iterate on the JSON without rebuilding, edit the ConfigMap with `dashboard/load-dashboard.sh`; the operator rewrites it from the embedded file on its next start.

## Verify

```bash
# traces: all three services have traces and one chat-client trace contains ogx-server and vllm spans
oc apply -f 07-verify/verify-traces.yaml && oc logs -f job/verify-traces -n genai-demo

# metrics: every metric family used by the dashboard has series in Thanos (needs cluster-admin; creates a reader service account)
07-verify/check_metrics.sh

# the dashboard ConfigMap exists with the console label and the expected title
07-verify/check_dashboard.sh
```

Expected result of the trace check: `trace <id> services: chat-client,ogx-server,vllm` and `OK: chat-client -> ogx-server -> vllm in one trace`.

Look at it yourself:

- **Traces:** open the Jaeger UI route (`oc get route tempo-genai-jaegerui -n genai-demo`), pick service `chat-client` and open a trace.
  The span attributes include `gen_ai.request.model`, `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`.
  For **Observe > Traces** in the console install the Cluster Observability Operator (`../operators/coo-install.yaml`) and apply `01-tracing/traces-ui-plugin.yaml`; this was not tested here.
- **Metrics:** Observe > Metrics, for example `sum(rate(vllm:generation_tokens_total[5m]))` or
  `histogram_quantile(0.95, sum by (le, gen_ai_request_model) (rate(traces_span_metrics_duration_seconds_bucket{gen_ai_operation_name!=""}[5m])))`.
- **Prompts and completions:** `oc logs -n genai-demo deploy/genai-collector` (log events from the `debug` exporter).

Measured on the demo cluster (float32, 11 compute threads): about 7.5 generated tokens per second for a single stream, about 30 tokens per second with 4 concurrent requests,
time to first token around 0.4 to 0.6 s for streaming requests, P95 request latency about 28 s for 96 generated tokens under load, 25 s to load the model.

## Demo script

About 10 minutes.

1. **The stack** (2 min): `oc get pods,otelcol,tempomonolithic,ogxserver -n genai-demo`. Explain: vLLM on CPU, OGX in front, one collector, Tempo.
2. **The collector** (2 min): show the pipelines in `02-collector/otel-collector.yaml`. Point at `transform/vllm-semconv` (aligning a non-conformant source) and `span_metrics` (metrics from traces).
3. **A trace** (2 min): Jaeger UI, service `chat-client`: the waterfall shows the client call, the OGX handling and the vLLM request with queue, prefill and decode time, plus the token counts.
4. **The dashboard** (3 min): Observe > Dashboards > OpenTelemetry GenAI. Walk the rows from overview to the vLLM engine. Start the load generator
   (`oc delete job loadgen -n genai-demo; oc apply -f 06-load/loadgen.yaml`) and watch requests running, KV cache usage and latency react.
5. **Where it comes from** (1 min): `oc get cm opentelemetry-genai -n openshift-config-managed -o yaml | head` and the operator file `internal/openshift/dashboards/dashboards.go`.

Prepare before the audience arrives: let vLLM finish its first request (kernel compilation) and run the load generator for a few minutes so the graphs have history.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| vLLM crash loops with `VLLM_PORT '...' appears to be a URI` | The Service is called `vllm`, so Kubernetes injects `VLLM_PORT=tcp://...` into pods. The Deployment sets `enableServiceLinks: false`; keep it. |
| First chat request hangs for 5 to 10 minutes, then the client logs `Request timed out` | vLLM compiles CPU kernels on the first request on a single thread. It finishes by itself (the client timeout is 300 s). Send one request after every vLLM restart. |
| `NUMA binding` and `numa_migrate_pages failed` warnings in the vLLM log | Harmless without the `SYS_NICE` capability. |
| OGX lists no `vllm/qwen2.5-1.5b` model, client logs `waiting for the model list` | OGX registers the model when it starts while vLLM is already serving. `oc rollout restart deploy/genai -n genai-demo`. |
| Client fails with `Model ... is of type 'rerank'` or picks a `claude-*` model | OGX also lists embedding, reranker and static provider models. The client filters on the `vllm/` prefix (`MODEL_PREFIX` overrides it). |
| Client traces contain no OGX span | The httpx instrumentation is missing from the client. |
| Dashboard panels show `-` or "No datapoints found" | Open it with Project: All Projects. Check that the variable is not named `namespace` (console quirk above). Check the data with `07-verify/check_metrics.sh`. |
| Dashboard does not exist | The operator was not built from the fork or `OPENSHIFT_CREATE_DASHBOARD` is false. Run `dashboard/load-dashboard.sh`. |
| `Tempo ... not supported on OpenShift` warning when applying TempoMonolithic | TempoMonolithic without multi-tenancy has no authentication on the ingest and query paths. Fine for a demo, not for production. |
| vLLM pod is rejected by the SCC or crashes on seccomp | Apply `03-inference/vllm-scc.yaml` and follow the patch in its header. Not needed on the verified cluster. |
| Pod `Pending` with insufficient CPU | vLLM requests 12 CPU; it needs a worker with at least 16 vCPU. |
| Image pull rate limits from Docker Hub | Mirror `vllm/vllm-openai-cpu`, `ogxai/distribution-starter` and `ubi9/python-312` to a registry you control. |

## Variations

- **bfloat16 on newer CPUs:** on `m7i` or newer, set `--dtype=bfloat16` in `03-inference/vllm.yaml`; this roughly halves the memory traffic per token.
- **Another model:** change the model argument and `--served-model-name`. The OGX model name and the client's prefix filter follow automatically. Gated models need an `HF_TOKEN` secret.
- **GPU:** use `vllm/vllm-openai`, request `nvidia.com/gpu: 1` and install the NFD and NVIDIA GPU operators first. Not tested.
- **More traffic:** raise `DURATION_SECONDS` or the number of workers in `06-load/loadgen.yaml`; vLLM queues requests (see the waiting panel).
- **Stretch ideas:** the contrib `gen_ai_normalizer` processor (alpha) maps OpenInference and OpenLLMetry attributes to the GenAI conventions, for clients that use those libraries;
  it is not in the Red Hat build of OpenTelemetry collector today. OBI with `ebpf.payload_extraction.http.genai.openai.enabled: true` gives zero-code GenAI spans.
  A Perses version of the dashboard works when the Cluster Observability Operator is installed.

## Cleanup

```bash
oc delete namespace genai-demo
oc delete -f 00-cluster/tempo-operator.yaml
oc delete -f https://raw.githubusercontent.com/ogx-ai/ogx-k8s-operator/v0.17.0/release/operator-openshift.yaml
oc delete configmap opentelemetry-genai -n openshift-config-managed   # only if you loaded it with the script
```

The operator removes the two dashboard ConfigMaps by itself when it stops. User workload monitoring stays enabled.

## Status and limitations

- Verified manually, step by step, on OCP 5.0 (AWS): one trace across the three services, all 25 dashboard panels returning data and rendering in the console, and the three scripts in `07-verify/` passing.
  The complete `chainsaw test` run was not executed as one piece; the test definition passes `chainsaw lint` and every manifest in it was applied on the cluster.
- The dashboard and the collector use components from upstream OpenTelemetry. The operator branch is based on unreleased upstream `main` (operator 0.162.0) and is not part of any product release.
  The collector image is the upstream contrib image; with the Red Hat build of OpenTelemetry collector, check the component and connector names of that version (`span_metrics` was previously called `spanmetrics`).
- The GenAI semantic conventions are in development. Metric and attribute names, and the instrumentation packages, can change between releases (`opentelemetry-instrumentation-genai-openai` is a 1.3 beta).
- Upstream Llama Stack was renamed OGX in 2026. This demo pins OGX operator v0.17.0, which deploys image `ogxai/distribution-starter:1.4.1`.
- CPU inference is slow by design. The demo is about the telemetry, not about serving performance.
- Not tested: the Observe > Traces console page, a GPU node, OpenShift versions other than 5.0.
