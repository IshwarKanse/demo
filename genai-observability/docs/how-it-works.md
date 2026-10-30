# How the demo works

Details for the GenAI observability demo in [../README.md](../README.md): the components, the dashboard, a demo script and variations.

## Glossary

| Term | Meaning |
|---|---|
| **GenAI semantic conventions** | The OpenTelemetry standard names for spans, attributes, metrics and events of generative AI calls (`gen_ai.*`). See [below](genai-semantic-conventions.md). |
| **vLLM** | An open-source LLM inference server with an OpenAI-compatible API, its own Prometheus metrics and OpenTelemetry tracing. |
| **OGX** | Open GenAI Stack, the upstream project formerly called Llama Stack: a server that exposes one API (chat, responses, vector stores, tools) in front of inference providers such as vLLM. |
| **OpenInference, OpenLLMetry** | Third-party OpenTelemetry-based instrumentation libraries for LLM apps with their own attribute names; see [below](genai-semantic-conventions.md#instrumentation-that-does-not-use-the-conventions). |
| **TTFT** | Time to first token: the delay between the request and the first generated token. |
| **KV cache** | The attention key/value memory vLLM keeps per running request; when it is full, requests queue. |
| **Span metrics** | Request rate, errors and duration derived from traces by the collector's `span_metrics` connector. |
| **Tenant** | In Tempo's multi-tenant mode, an isolated trace namespace with its own access rules; this demo has one, `genai`. |
| **UIPlugin** | A resource of the Cluster Observability Operator that adds a page to the OpenShift console (here Observe > Traces). |

## What each piece does

### Collector (`02-collector/otel-collector.yaml`)

| Section | Configuration | Why |
|---|---|---|
| receivers | `otlp` (gRPC 4317, HTTP 4318); `prometheus/vllm` scraping `vllm.genai-demo.svc:8000` every 10 s | client, OGX and vLLM push OTLP; vLLM metrics are only available as a Prometheus endpoint |
| processors | `memory_limiter`, `k8sattributes`, `batch`, `transform/vllm-semconv` | see below |
| connector | `span_metrics` with histogram unit `s`, buckets 100 ms to 60 s, extra dimensions `gen_ai.request.model`, `gen_ai.operation.name`, `gen_ai.provider.name` | derives request rate, errors and latency per model from the traces |
| extension | `bearertokenauth` reading the ServiceAccount token | authenticates the export to the Tempo gateway |
| exporters | `otlphttp/tempo` (gateway URL for tenant `genai`, TLS with the service CA, bearer token, `X-Scope-OrgID: genai`), `prometheus` on `:8889` with `resource_to_telemetry_conversion`, `debug` | traces to Tempo, metrics to user workload monitoring |
| pipelines | traces: `otlphttp/tempo` and `span_metrics`; metrics: `otlp`, `prometheus/vllm`, `span_metrics` to Prometheus; logs: `otlp` to `debug` | |

`transform/vllm-semconv` exists because vLLM spans use the pre-stable GenAI attribute names (`gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`)
and lack `gen_ai.request.model`, `gen_ai.operation.name` and `gen_ai.provider.name`. The processor copies them to the current semantic convention names
for spans that carry vLLM's `gen_ai.request.id`, so vLLM spans line up with the client spans.

`observability.metrics.enableMetrics: true` makes the operator create the ServiceMonitors for the collector's own metrics and for the Prometheus exporter.
The collector image is the upstream contrib one (`opentelemetry-collector-contrib:0.162.0`) because the community operator injects the core image by default, which lacks several of these components.
`resource_to_telemetry_conversion` is deprecated in contrib 0.162 and still works.

### Tracing (`01-tracing/`)

Tempo runs as a **multi-tenant TempoStack** (`tenants.mode: openshift`) behind its gateway, which is what the console's tracing page needs.

- **Storage:** SeaweedFS (`seaweedfs.yaml`), an S3 gateway in one pod with the bucket `tempo`. The S3 secret key is generated when you deploy (`create-storage-secret.sh` creates the Secret `tempo-storage`, which SeaweedFS and the TempoStack both read; it keeps an existing Secret and replaces one whose key is empty or is the old public demo value); no credentials are in the repository. The upstream MinIO community image on quay.io is no longer public; the SeaweedFS image is the multi-arch build the operator e2e tests use.
- **Tenant:** one tenant, `genai` (`tempostack.yaml`). Its name appears in the gateway URL (`/api/traces/v1/genai`), in the `X-Scope-OrgID` header and in the RBAC rules.
- **Writers** (`rbac.yaml`): the collector ServiceAccount `genai-collector` has the verb `create` on resource `genai`, resource name `traces`, in API group `tempo.grafana.com`.
- **Readers:** the verb `get` on the same resource, bound to the group `genai-trace-readers` (add users with `oc adm groups new genai-trace-readers <user>`; cluster admins need no binding). With gateway RBAC enabled, readers see only the traces of the namespaces they can access
  (matched on the span attribute `k8s.namespace.name`, which the collector's `k8sattributes` processor adds); cluster admins see all traces.
  The service account `trace-reader` used by the check Job gets the `view` role in `genai-demo` for that reason.
- **UI:** `traces-ui-plugin.yaml` creates a `UIPlugin` of type `DistributedTracing`; the Cluster Observability Operator (installed by `00-cluster/coo-operator.yaml`) adds **Observe > Traces**, discovers the TempoStack and queries it as the logged in user.

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

## Demo script

About 10 minutes.

1. **The stack** (2 min): `oc get pods,otelcol,tempostack,ogxserver -n genai-demo`. Explain: vLLM on CPU, OGX in front, one collector, Tempo.
2. **The collector** (2 min): show the pipelines in `02-collector/otel-collector.yaml`. Point at `transform/vllm-semconv` (aligning a non-conformant source) and `span_metrics` (metrics from traces).
3. **A trace** (2 min): **Observe > Traces**, instance `genai-demo / genai`: open a `chat-client` trace. The waterfall shows the client call, the OGX handling and the vLLM request, plus the token counts in the span attributes.
   Mention that Tempo is multi-tenant: the console reads through the gateway with your own token.
4. **The dashboard** (3 min): Observe > Dashboards > OpenTelemetry GenAI. Walk the rows from overview to the vLLM engine. Start the load generator
   (`oc delete job loadgen -n genai-demo; oc apply -f 06-load/loadgen.yaml`) and watch requests running, KV cache usage and latency react.
5. **Where it comes from** (1 min): `oc get cm opentelemetry-genai -n openshift-config-managed -o yaml | head` and the operator file `internal/openshift/dashboards/dashboards.go`.

Prepare before the audience arrives: let vLLM finish its first request (kernel compilation) and run the load generator for a few minutes so the graphs have history.

## Variations

- **bfloat16 on newer CPUs:** on `m7i` or newer, set `--dtype=bfloat16` in `03-inference/vllm.yaml`; this roughly halves the memory traffic per token.
- **Another model:** change the model argument and `--served-model-name`. The OGX model name and the client's prefix filter follow automatically. Gated models need an `HF_TOKEN` secret.
- **GPU:** use `vllm/vllm-openai`, request `nvidia.com/gpu: 1` and install the NFD and NVIDIA GPU operators first. Not tested.
- **More traffic:** raise `DURATION_SECONDS` or the number of workers in `06-load/loadgen.yaml`; vLLM queues requests (see the waiting panel).
- **Stretch ideas:** the contrib `gen_ai_normalizer` processor (alpha) maps OpenInference and OpenLLMetry attributes to the GenAI conventions, for clients that use those libraries;
  it is not in the Red Hat build of OpenTelemetry collector today. OBI with `ebpf.payload_extraction.http.genai.openai.enabled: true` gives zero-code GenAI spans.
  A Perses version of the dashboard works when the Cluster Observability Operator is installed.
