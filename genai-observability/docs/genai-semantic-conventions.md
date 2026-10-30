<!-- Part of the GenAI observability demo, see ../README.md -->

# GenAI semantic conventions

Background for the demo in [../README.md](../README.md): what the OpenTelemetry GenAI conventions are, which names the demo uses, and the instrumentation available today.

OpenTelemetry defines an open standard for describing generative AI operations: the **GenAI semantic conventions**. They give spans, attributes, metrics and events the same names whichever
library produced them and whichever backend consumes them, so one dashboard or alert works across providers and frameworks (`gen_ai.request.model` instead of a different name per vendor).
The conventions are developed by the OpenTelemetry GenAI special interest group in the repository [semantic-conventions-genai](https://github.com/open-telemetry/semantic-conventions-genai)
and published on [opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/gen-ai/).

**Status: Development.** The conventions are not stable yet. Names and structure still change between versions (this demo already shows two generations of the token metric, see below),
and instrumentation packages are pre-1.0 or beta. Pin versions and expect to adapt queries and dashboards when you upgrade.

## What the specification covers

| Area | What it defines | Specification |
|---|---|---|
| Overview and status | scope and stability | [README](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/README.md) |
| Client inference | spans, events and metrics of a chat or completion call | [client-inference](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-inference.md) |
| Embeddings | spans and metrics of embedding calls | [client-embeddings](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/client-embeddings.md) |
| Model spans | span name, kind and attributes of model operations | [gen-ai-spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md) |
| Agent spans | `invoke_agent`, `create_agent`, tool execution, workflows | [gen-ai-agent-spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md) |
| Metrics | client and server metrics, for example operation duration, time to first token | [gen-ai-metrics](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-metrics.md) |
| Token metrics | input and output token counters, cache and reasoning tokens | [gen-ai-token-metrics](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-token-metrics.md) |
| Events | prompts, completions and other inputs and outputs | [gen-ai-events](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-events.md) |
| Exceptions | errors of GenAI operations | [gen-ai-exceptions](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-exceptions.md) |
| Provider specifics | OpenAI, Anthropic, Azure AI Inference, AWS Bedrock | [openai](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/openai.md), [anthropic](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/anthropic.md), [azure-ai-inference](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/azure-ai-inference.md), [aws-bedrock](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/aws-bedrock.md) |
| Protocols | Model Context Protocol and Agent2Agent | [mcp](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/mcp.md), [a2a](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/a2a.md) |

The attribute registry (all `gen_ai.*` keys with types and examples) is on [opentelemetry.io](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/).
To get started read the overview, then client inference, spans and metrics.

## The names this demo relies on

| Name | Kind | Meaning |
|---|---|---|
| `gen_ai.operation.name` | span and metric attribute | Operation type: `chat`, `embeddings`, `generate_content`, `retrieval`, `execute_tool`, `invoke_agent`, `create_agent`, `invoke_workflow` |
| `gen_ai.provider.name` | attribute | Provider of the model API, for example `openai` or `vllm` |
| `gen_ai.request.model`, `gen_ai.response.model` | attribute | Model asked for and model that answered |
| `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens` | span attribute | Tokens in the prompt and in the completion |
| `gen_ai.client.operation.duration` | histogram, seconds | Duration of a client call |
| `gen_ai.client.token.usage` | histogram, with `gen_ai.token.type` = `input` or `output` | Token usage as emitted by the installed instrumentation (schema 1.37) |
| `gen_ai.client.inference.usage.input_tokens`, `...output_tokens` | counters | The newer replacement of the token histogram in the current specification |
| `gen_ai.client.operation.time_to_first_chunk`, `...time_per_output_chunk` | histograms, seconds | Streaming latency as emitted by the installed instrumentation |
| `gen_ai.server.request.duration`, `gen_ai.server.time_to_first_token`, `gen_ai.server.time_per_output_token` | histograms, seconds | Server-side metrics defined by the specification; the servers in this demo expose their own metric names instead |

In Prometheus the dots become underscores and units are appended, for example `gen_ai_client_operation_duration_seconds_bucket`, and attributes become labels (`gen_ai_request_model`).
The dashboard queries in `dashboard/genai-dashboard.json` use these Prometheus names.

## Which part of the demo follows the conventions

| Component | Follows the conventions? | Details |
|---|---|---|
| Chat client | Yes | `opentelemetry-instrumentation-genai-openai` 1.3b0 emits GenAI spans and the `gen_ai.client.*` metrics, with schema URL 1.37.0 on the instrumentation scope |
| OGX server | Not for its metrics | Emits HTTP server spans and its own metrics (`ogx_inference_*`, `ogx_concurrent_requests`, `ogx_requests_total`); no GenAI attributes were observed on its spans in this setup |
| vLLM | Partly | Spans use older names, which the collector fixes (below); its metrics are its own `vllm:*` Prometheus metrics, not `gen_ai.server.*` |
| Collector | Adds the missing pieces | `transform/vllm-semconv` renames vLLM span attributes; `span_metrics` turns every span with GenAI attributes into request, error and latency metrics per model |

**vLLM span attributes rewritten by the collector** (`transform/vllm-semconv` in `02-collector/otel-collector.yaml`):

| vLLM emits | Collector writes |
|---|---|
| `gen_ai.usage.prompt_tokens` | `gen_ai.usage.input_tokens` |
| `gen_ai.usage.completion_tokens` | `gen_ai.usage.output_tokens` |
| `gen_ai.response.model` (no request model) | also `gen_ai.request.model` |
| nothing | `gen_ai.operation.name` = `chat` and `gen_ai.provider.name` = `vllm` |

## Instrumentation libraries available today

OpenTelemetry ships GenAI instrumentation next to the conventions. Status as checked on 2026-10-30; the libraries are pre-1.0 or beta and change together with the conventions.

| Language | Where | What it covers |
|---|---|---|
| Python | [opentelemetry-python-genai](https://github.com/open-telemetry/opentelemetry-python-genai/tree/main/instrumentation) (packages named `opentelemetry-instrumentation-genai-*`) | Providers: OpenAI, Anthropic, AWS Bedrock, Google GenAI. Frameworks: LangChain, LlamaIndex, DSPy, CrewAI, Agno, smolagents, Portkey. Agent SDKs: OpenAI Agents, Claude Agent SDK, Qwen-Agent, QwenPaw. Vector database: Weaviate client. |
| Python (shared code) | [opentelemetry-util-genai](https://github.com/open-telemetry/opentelemetry-python-genai/tree/main/util/opentelemetry-util-genai) | Helpers the instrumentations use to emit spans, metrics and events |
| Python (older location) | [opentelemetry-python-contrib, instrumentation-genai](https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation-genai) | `openai-v2` (deprecated, replaced by `genai-openai`), `openai-agents-v2`, `vertexai` |
| Java | [opentelemetry-java-instrumentation, openai](https://github.com/open-telemetry/opentelemetry-java-instrumentation/tree/main/instrumentation/openai) | OpenAI client |
| JavaScript | [opentelemetry-js-contrib](https://github.com/open-telemetry/opentelemetry-js-contrib/tree/main/packages/instrumentation-openai) | `instrumentation-openai`, [`instrumentation-langchain`](https://github.com/open-telemetry/opentelemetry-js-contrib/tree/main/packages/instrumentation-langchain), `instrumentation-openai-agents`, [`genai-util`](https://github.com/open-telemetry/opentelemetry-js-contrib/tree/main/packages/genai-util) |
| Any language, no code changes | [OBI](https://github.com/open-telemetry/opentelemetry-ebpf-instrumentation) (OpenTelemetry eBPF instrumentation) | Extracts GenAI payloads from HTTP traffic of OpenAI, Anthropic, Gemini, Bedrock and Qwen style APIs; a technology preview in the Red Hat collector, not used in this demo |

No Go or .NET GenAI instrumentation was found in a quick search of the OpenTelemetry organisation; that does not prove none exists.

On PyPI the Python packages are published under the same names; the ones checked on 2026-10-30 were
[`opentelemetry-instrumentation-genai-openai`](https://pypi.org/project/opentelemetry-instrumentation-genai-openai/),
[`-genai-anthropic`](https://pypi.org/project/opentelemetry-instrumentation-genai-anthropic/),
[`-genai-langchain`](https://pypi.org/project/opentelemetry-instrumentation-genai-langchain/),
[`opentelemetry-instrumentation-google-genai`](https://pypi.org/project/opentelemetry-instrumentation-google-genai/) and
[`opentelemetry-util-genai`](https://pypi.org/project/opentelemetry-util-genai/), all at 1.3b0.

Two things to watch:

- **Package names can mislead.** `opentelemetry-instrumentation-langchain` and `opentelemetry-instrumentation-vertexai` (without `genai`) on PyPI are the OpenLLMetry project's packages, not the OpenTelemetry project's. Check the publisher and the repository before installing.
- **Operator auto-instrumentation does not include them.** The [OpenTelemetry operator's automatic instrumentation](https://opentelemetry.io/docs/platforms/kubernetes/operator/automatic/) injects its own Python instrumentation image, and that image contains no GenAI package
  (checked in the operator's `autoinstrumentation/python/requirements.txt`). With an `Instrumentation` resource you would have to build a custom image that adds the GenAI packages, or install them in the application as this demo's client does.
  The Red Hat build of OpenTelemetry documents that it supports only the injection mechanism, not the instrumentation libraries or the upstream images, and it does not ship a Python instrumentation image.

## Instrumentation settings that matter

| Setting | Effect |
|---|---|
| `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` | Whether prompts and completions are recorded. For `opentelemetry-instrumentation-genai-openai` the values are `no_content` (default), `span_only`, `event_only` and `span_and_event`; verify against the changelog of the version you use. The demo sets `span_and_event` on the client and `true` on OGX. **Prompts and completions can contain personal or confidential data; turn this off or filter it in production.** |
| `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` | Needed by the older, now deprecated `opentelemetry-instrumentation-openai-v2` package to emit the newer attribute shapes. The demo uses the newer package, which does not need it. |
| `OTEL_METRIC_EXPORT_INTERVAL` | Metric export period in milliseconds; the demo uses 5000 so that dashboards react quickly (default 60000). |

## Instrumentation that does not use the conventions

Two popular open-source projects instrument LLM applications with OpenTelemetry but predate the standard and use their own attribute names:
[OpenInference](https://github.com/Arize-ai/openinference) (Arize AI, for example `llm.token_count.prompt`, `llm.model_name`, `openinference.span.kind`) and
[OpenLLMetry](https://github.com/traceloop/openllmetry) (Traceloop, for example `llm.usage.prompt_tokens`, `llm.request.model`, `traceloop.span.kind`).
A dashboard written for the GenAI conventions cannot read their data directly.

The upstream collector-contrib component [`gen_ai_normalizer`](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/genainormalizerprocessor)
(alpha, traces only) rewrites their attributes to the GenAI conventions, and lets you define mappings for other sources:

```yaml
processors:
  gen_ai_normalizer:
    sources:
      - name: openinference
        remove_originals: true
      - name: openllmetry
        remove_originals: true
service:
  pipelines:
    traces:
      processors: [memory_limiter, k8sattributes, gen_ai_normalizer, batch]
```

It is **not used in this demo** (the demo's clients already emit the conventions) and it is not in the Red Hat build of OpenTelemetry collector today; it is part of the upstream contrib image the demo runs.
Adding an OpenInference-instrumented client plus this processor is a natural extension, see [Variations](how-it-works.md#variations).
