# Window 1: (1792651984, 1792652704] = 12 min

## Typed path (Prometheus main with metadata -> contrib nightly receiver)

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 9 |
| samples_dump_matched_series | 31222 |
| samples_equal | 31213 |
| samples_source | 31213 |
| series_dump | 655 |
| series_exact | 655 |
| series_only_dump | 0 |
| series_only_source | 1082 |
| series_source | 1737 |

Series only in the source (not emitted), by family:

| family | series |
|---|---|
| avalanche_histogram_metric_mmmmm_0_0_bucket | 160 |
| avalanche_histogram_metric_mmmmm_0_1_bucket | 160 |
| prometheus_http_request_duration_seconds_bucket | 70 |
| prometheus_http_response_size_bytes_bucket | 63 |
| avalanche_summary_metric_mmmmm_0_0 | 40 |
| prometheus_target_sync_length_histogram_seconds_bucket | 25 |
| prometheus_target_sync_length_seconds | 25 |
| avalanche_histogram_metric_mmmmm_0_0_count | 20 |
| avalanche_histogram_metric_mmmmm_0_0_sum | 20 |
| avalanche_histogram_metric_mmmmm_0_1_count | 20 |
| avalanche_histogram_metric_mmmmm_0_1_sum | 20 |
| avalanche_summary_metric_mmmmm_0_0_count | 20 |
| avalanche_summary_metric_mmmmm_0_0_sum | 20 |
| corr_latency_seconds_bucket | 20 |
| prometheus_engine_query_duration_histogram_seconds_bucket | 20 |
| prometheus_remote_storage_sent_batch_duration_seconds_bucket | 16 |
| prometheus_tsdb_compaction_duration_seconds_bucket | 15 |
| prometheus_tsdb_selected_series_compaction_duration_seconds_bucket | 15 |
| prometheus_tsdb_stale_series_compaction_duration_seconds_bucket | 15 |
| prometheus_tsdb_compaction_chunk_samples_bucket | 13 |
| prometheus_tsdb_compaction_chunk_size_bytes_bucket | 13 |
| go_gc_heap_allocs_by_size_bytes_bucket | 12 |
| go_gc_heap_frees_by_size_bytes_bucket | 12 |
| prometheus_engine_query_duration_seconds | 12 |
| prometheus_tsdb_compaction_chunk_range_seconds_bucket | 11 |
| go_gc_pauses_seconds_bucket | 8 |
| go_sched_latencies_seconds_bucket | 8 |
| go_sched_pauses_stopping_gc_seconds_bucket | 8 |
| go_sched_pauses_stopping_other_seconds_bucket | 8 |
| go_sched_pauses_total_gc_seconds_bucket | 8 |
| go_sched_pauses_total_other_seconds_bucket | 8 |
| prometheus_tsdb_sample_ooo_delta_bucket | 8 |
| prometheus_http_request_duration_seconds_count | 7 |
| prometheus_http_request_duration_seconds_sum | 7 |
| prometheus_http_response_size_bytes_count | 7 |
| prometheus_http_response_size_bytes_sum | 7 |
| corr_summary_seconds | 6 |
| prometheus_sd_consul_rpc_duration_seconds | 6 |
| go_gc_duration_seconds | 5 |
| prometheus_rule_evaluation_duration_histogram_seconds_bucket | 5 |
| prometheus_rule_group_duration_histogram_seconds_bucket | 5 |
| prometheus_rule_group_duration_seconds | 5 |
| prometheus_target_interval_length_histogram_seconds_bucket | 5 |
| prometheus_target_interval_length_seconds | 5 |
| prometheus_target_sync_length_histogram_seconds_count | 5 |
| prometheus_target_sync_length_histogram_seconds_sum | 5 |
| prometheus_target_sync_length_seconds_count | 5 |
| prometheus_target_sync_length_seconds_sum | 5 |
| prometheus_engine_query_duration_histogram_seconds_count | 4 |
| prometheus_engine_query_duration_histogram_seconds_sum | 4 |
| prometheus_engine_query_duration_seconds_count | 4 |
| prometheus_engine_query_duration_seconds_sum | 4 |
| prometheus_rule_evaluation_duration_seconds | 3 |
| prometheus_sd_file_scan_duration_seconds | 3 |
| prometheus_sd_kuma_fetch_duration_seconds | 3 |
| prometheus_tsdb_wal_fsync_duration_seconds | 3 |
| target_info | 3 |
| corr_latency_seconds_count | 2 |
| corr_latency_seconds_sum | 2 |
| corr_summary_seconds_count | 2 |

Series only in the dump (no TSDB counterpart), by family:

| family | series |
|---|---|

Examples `extra_nan_in_dump` (9 shown):

- corr_build_info{commit="abcdef0",version="1.2.3"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_temperature_celsius{sensor="normal"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_temperature_celsius{sensor="neginf"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_requests_total{path="/b"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_requests_total{path="/a"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_temperature_celsius{sensor="nan"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_escape{weird="quote" backslash\ newline
 tab	 unicode ü 日本"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_temperature_celsius{sensor="posinf"} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]
- corr_resetting_total{} instance=stale-app.otel-correctness.svc:8080 job=stale-app [1792652320711]

### Native histograms and NHCB

| histogram series / points | count |
|---|---|
| explicit_points | 2789 |
| exponential_points | 2213 |
| points_equal | 5002 |
| points_source | 5002 |
| series_dump | 106 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 106 |

NoRecordedValue flagged points in the dump: 0 on 0 series

### Metadata: Prometheus type/unit -> OTLP kind/monotonic/prometheus.type/unit, start timestamps set (points with startTimeUnixNano / points)

| metric | src type | src unit | kind | monotonic | prometheus.type | unit | description | start ts |
|---|---|---|---|---|---|---|---|---|
| avalanche_counter_metric_mmmmm_0_0_total | counter |  | sum | True | counter |  | Metric avalanche_counter_metric_mmmmm_0_ | 0/4740 |
| avalanche_counter_metric_mmmmm_0_1_total | counter |  | sum | True | counter |  | Metric avalanche_counter_metric_mmmmm_0_ | 0/4740 |
| avalanche_counter_metric_mmmmm_0_2_total | counter |  | sum | True | counter |  | Metric avalanche_counter_metric_mmmmm_0_ | 0/4740 |
| avalanche_gauge_metric_mmmmm_0_0 | gauge |  | gauge | None | gauge |  | Metric avalanche_gauge_metric_mmmmm_0_0  | 0/4740 |
| avalanche_gauge_metric_mmmmm_0_1 | gauge |  | gauge | None | gauge |  | Metric avalanche_gauge_metric_mmmmm_0_1  | 0/4740 |
| avalanche_gauge_metric_mmmmm_0_2 | gauge |  | gauge | None | gauge |  | Metric avalanche_gauge_metric_mmmmm_0_2  | 0/4740 |
| avalanche_histogram_metric_mmmmm_0_0 | histogram |  | histogram | None | histogram |  | Metric avalanche_histogram_metric_mmmmm_ | 0/4740 |
| avalanche_histogram_metric_mmmmm_0_1 | histogram |  | histogram | None | histogram |  | Metric avalanche_histogram_metric_mmmmm_ | 0/4740 |
| avalanche_native_histogram_metric_mmmmm_0_0 | histogram |  | exponentialHistogram | None | histogram |  | Metric avalanche_native_histogram_metric | 0/4740 |
| corr_build_info | ? |  | sum | None | info |  | Build information. | 0/277 |
| corr_escape | gauge |  | gauge | None | gauge |  | Gauge whose label value needs escaping. | 0/277 |
| corr_latency_seconds | histogram | seconds | histogram | None | histogram | s | Request latency, with trace exemplars. | 0/227 |
| corr_requests_total | counter | requests | sum | True | counter | requests | Requests handled, with trace exemplars. | 0/556 |
| corr_resetting_total | counter |  | sum | True | counter |  | Counter that resets every 150 seconds. | 0/305 |
| corr_temperature_celsius | gauge | celsius | gauge | None | gauge | Cel | Gauge with ordinary, NaN, +Inf and -Inf  | 0/1108 |
| go_gc_heap_allocs_by_size_bytes | histogram | bytes | histogram | None | histogram | By | Distribution of heap allocations by appr | 0/238 |
| otelcol_receiver_accepted_metric_points | counter |  | sum | True | counter |  | Number of metric points successfully pus | 0/683 |
| prometheus_http_request_duration_seconds | histogram |  | exponentialHistogram | None | histogram |  | Histogram of latencies for HTTP requests | 0/1465 |
| prometheus_remote_storage_samples_total | counter |  | sum | True | counter |  | Total number of samples sent to remote s | 0/238 |
| scrape_duration_seconds | ? |  | gauge | None | gauge | s | Duration of the last scrape in seconds. | 0/1661 |
| scrape_samples_post_metric_relabeling | ? |  | gauge | None | gauge | samples | Number of samples remaining after metric | 0/1661 |
| scrape_samples_scraped | ? |  | gauge | None | gauge | samples | Number of samples last scraped. | 0/1661 |
| scrape_series_added | ? |  | gauge | None | gauge | series | Number of series in the last scrape. | 0/1661 |
| up | ? |  | gauge | None | gauge | targets | Health of the scrape target. 1 means the | 0/1661 |

Kinds over all 310 families (src type, kind, monotonic -> families): {"('counter', 'sum', 'True')": 153, "('gauge', 'gauge', 'None')": 121, "('histogram', 'histogram', 'None')": 15, "('histogram', 'exponentialHistogram', 'None')": 15, "('?', 'sum', 'None')": 1, "('?', 'gauge', 'None')": 5}

Scopes: {"('OpenTelemetry Collector Contrib', '0.163.1')": 1664}

### Exemplars (window 1): source exemplar storage vs dump, matched on trace id, span id, value, timestamp and the other labels

| series | source | dump | equal | only source | only dump |
|---|---|---|---|---|---|
| corr_latency_seconds{} instance=exemplar-app.otel-correctness.svc:8080 job=exemplar-app | 96 | 96 | 96 | 0 | 0 |
| corr_latency_seconds_bucket{le="0.05"} instance=stale-app.otel-correctness.svc:8080 job=stale-app | 22 | 0 | 0 | 22 | 0 |
| corr_latency_seconds_bucket{le="0.5"} instance=stale-app.otel-correctness.svc:8080 job=stale-app | 22 | 0 | 0 | 22 | 0 |
| corr_requests_total{path="/a"} instance=exemplar-app.otel-correctness.svc:8080 job=exemplar-app | 48 | 48 | 48 | 0 | 0 |
| corr_requests_total{path="/b"} instance=exemplar-app.otel-correctness.svc:8080 job=exemplar-app | 48 | 48 | 48 | 0 | 0 |
| corr_requests_total{path="/a"} instance=stale-app.otel-correctness.svc:8080 job=stale-app | 22 | 22 | 22 | 0 | 0 |
| corr_requests_total{path="/b"} instance=stale-app.otel-correctness.svc:8080 job=stale-app | 22 | 22 | 22 | 0 | 0 |

First dump exemplar: `{"timeUnixNano": "1792651990691000000", "asDouble": 1, "traceId": "72ff1d46e5cb4e6b86a411843eed5a79", "spanId": "5572df6fe80d77ad"}`
First source exemplar: `{"labels": {"span_id": "f9eb26e22c592358", "trace_id": "1b13cbe1bb5264a73f67ab8d812bbef3"}, "value": "0.045000000000000005", "timestamp": 1792651990.691}`

## Production path, dump of `prod` (platform Prometheus 3.13.2, both replicas)

### replica prometheus-k8s-0

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 77612 |
| samples_equal | 77609 |
| samples_source | 77609 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="app",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",image="HOST/ubi9/python-312:latest",metrics_path="/metrics/cadvisor",name="k8s_app_stale-app-6599f7cbc6-5kbjp_otel-correctness_UUID_0",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652315928]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-conmon-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",metrics_path="/metrics/cadvisor",node="node-2",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652315928]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652345928]
### replica prometheus-k8s-1

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 77621 |
| samples_equal | 77618 |
| samples_source | 77618 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="app",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",image="HOST/ubi9/python-312:latest",metrics_path="/metrics/cadvisor",name="k8s_app_stale-app-6599f7cbc6-5kbjp_otel-correctness_UUID_0",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652331818]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-conmon-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",metrics_path="/metrics/cadvisor",node="node-2",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652331818]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652331818]

Metadata on the production path (kind, prometheus.type, unit, has description -> families): {"('gauge', 'unknown', '', False)": 31}
Points with startTimeUnixNano: 0 of 583928
Points with an empty resource (no job/instance, e.g. ALERTS): 336
Resource splits (job/instance pairs seen with more than one resource attribute set): 0 of 154 pairs
Scopes: {"('Red Hat build of OpenTelemetry', '0.158.0')": 63673}

## Production path, dump of `prod-contrib` (platform Prometheus 3.13.2, both replicas)

### replica prometheus-k8s-0

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 77612 |
| samples_equal | 77609 |
| samples_source | 77609 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="app",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",image="HOST/ubi9/python-312:latest",metrics_path="/metrics/cadvisor",name="k8s_app_stale-app-6599f7cbc6-5kbjp_otel-correctness_UUID_0",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652315928]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-conmon-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",metrics_path="/metrics/cadvisor",node="node-2",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652315928]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652345928]
### replica prometheus-k8s-1

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 77621 |
| samples_equal | 77618 |
| samples_source | 77618 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="app",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",image="HOST/ubi9/python-312:latest",metrics_path="/metrics/cadvisor",name="k8s_app_stale-app-6599f7cbc6-5kbjp_otel-correctness_UUID_0",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652331818]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice/crio-conmon-c7981d3140d7adf527d668d826d5eacb75fcfb4b24eb84f3be12f30cd62e9727.scope",metrics_path="/metrics/cadvisor",node="node-2",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652331818]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-poda5bc9eb4_873c_492d_8b8c_c4f9366849d8.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-2",pod="stale-app-6599f7cbc6-5kbjp",service="kubelet"} instance=IP-4:10250 job=kubelet [1792652331818]

Metadata on the production path (kind, prometheus.type, unit, has description -> families): {"('gauge', 'unknown', '', False)": 31}
Points with startTimeUnixNano: 0 of 643774
Points with an empty resource (no job/instance, e.g. ALERTS): 336
Resource splits (job/instance pairs seen with more than one resource attribute set): 0 of 154 pairs
Scopes: {"('OpenTelemetry Collector Contrib', '0.163.1')": 48249}

Typed path resource pairs: 7, splits: 0; extra resource attributes seen: ["service_instance_id", "service_name", "service_version"]

## Counters at the window boundaries (value at start, at end, delta)

| where | metric | name | start | end | delta |
|---|---|---|---|---|---|
| typed | prometheus_remote_storage_exemplars_failed_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_exemplars_total | typed | 216.0 | 500.0 | 284.0 |
| typed | prometheus_remote_storage_histograms_failed_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_histograms_pending | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_histograms_retried_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_histograms_total | typed | 3709.0 | 8709.0 | 5000.0 |
| typed | prometheus_remote_storage_samples_failed_total | typed | 37121.0 | 87493.0 | 50372.0 |
| typed | prometheus_remote_storage_samples_pending | typed | 25.0 | 25.0 | 0.0 |
| typed | prometheus_remote_storage_samples_retried_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_samples_total | typed | 61640.0 | 143387.0 | 81747.0 |
| typed | prometheus_remote_storage_sent_batch_duration_seconds_count | typed | 114.0 | 258.0 | 144.0 |
| typed | prometheus_remote_storage_shards | typed | 1.0 | 1.0 | 0.0 |
| typed | prometheus_tsdb_head_samples_appended_total |  | 62645.0 | 144392.0 | 81747.0 |
| typed | prometheus_tsdb_head_samples_appended_total |  | 3786.0 | 8786.0 | 5000.0 |
| typed | prometheus_tsdb_head_series |  | 1818.0 | 1843.0 | 25.0 |
| prod0 | prometheus_remote_storage_exemplars_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_exemplars_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_pending | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_pending | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_pending | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_pending | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_histograms_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_metadata_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_metadata_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_metadata_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_metadata_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod | 1141.0 | 281.0 | -860.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod-contrib | 997.0 | 281.0 | -716.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod | 1387.0 | 548.0 | -839.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod-contrib | 1387.0 | 548.0 | -839.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_total | prod | 5012000.0 | 15498000.0 | 10486000.0 |
| prod0 | prometheus_remote_storage_samples_total | prod-contrib | 5012000.0 | 15498000.0 | 10486000.0 |
| prod0 | prometheus_remote_storage_samples_total | prod | 4970000.0 | 15456000.0 | 10486000.0 |
| prod0 | prometheus_remote_storage_samples_total | prod-contrib | 4970000.0 | 15456000.0 | 10486000.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 2506.0 | 7749.0 | 5243.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 2506.0 | 7749.0 | 5243.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 2485.0 | 7728.0 | 5243.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 2485.0 | 7728.0 | 5243.0 |
| prod0 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 130956334.0 | 141441618.0 | 10485284.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 131170548.0 | 141655709.0 | 10485161.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_tsdb_head_series |  | 498157.0 | 498588.0 | 431.0 |
| prod0 | prometheus_tsdb_head_series |  | 495357.0 | 495786.0 | 429.0 |
| prod1 | prometheus_remote_storage_exemplars_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_exemplars_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_pending | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_pending | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_pending | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_pending | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_histograms_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_metadata_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_metadata_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_metadata_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_metadata_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_failed_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_failed_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod | 1389.0 | 580.0 | -809.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod-contrib | 1389.0 | 580.0 | -809.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod | 1336.0 | 518.0 | -818.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod-contrib | 1336.0 | 518.0 | -818.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_total | prod | 5176000.0 | 15662000.0 | 10486000.0 |
| prod1 | prometheus_remote_storage_samples_total | prod-contrib | 5176000.0 | 15662000.0 | 10486000.0 |
| prod1 | prometheus_remote_storage_samples_total | prod | 4980000.0 | 15466000.0 | 10486000.0 |
| prod1 | prometheus_remote_storage_samples_total | prod-contrib | 4980000.0 | 15466000.0 | 10486000.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 2588.0 | 7831.0 | 5243.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 2588.0 | 7831.0 | 5243.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 2490.0 | 7733.0 | 5243.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 2490.0 | 7733.0 | 5243.0 |
| prod1 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 131120726.0 | 141605917.0 | 10485191.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 131180497.0 | 141665679.0 | 10485182.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_tsdb_head_series |  | 498213.0 | 498588.0 | 375.0 |
| prod1 | prometheus_tsdb_head_series |  | 495357.0 | 495786.0 | 429.0 |
| otelcol prod | otelcol_exporter_queue_size | otlphttp | 0.0 | 2000.0 | 2000.0 |
| otelcol typed | otelcol_exporter_queue_size | otlphttp | 0.0 | 0.0 | 0.0 |
| otelcol prod | otelcol_exporter_sent_metric_points | file | 78340.0 | 233585.0 | 155245.0 |
| otelcol prod-contrib | otelcol_exporter_sent_metric_points | file | 78512.0 | 233771.0 | 155259.0 |
| otelcol typed | otelcol_exporter_sent_metric_points | file | 28606.0 | 64839.0 | 36233.0 |
| otelcol prod | otelcol_exporter_sent_metric_points | otlphttp | 10600000.0 | 31568000.0 | 20968000.0 |
| otelcol typed | otelcol_exporter_sent_metric_points | otlphttp | 28606.0 | 64839.0 | 36233.0 |
| otelcol prod | otelcol_process_memory_rss |  | 150048768.0 | 154230784.0 | 4182016.0 |
| otelcol prod-contrib | otelcol_process_memory_rss |  | 248778752.0 | 251461632.0 | 2682880.0 |
| otelcol typed | otelcol_process_memory_rss |  | 243855360.0 | 248528896.0 | 4673536.0 |
| otelcol prod | otelcol_process_uptime |  | 587.544781855 | 1307.544863238 | 720.0000813830001 |
| otelcol prod-contrib | otelcol_process_uptime |  | 590.516826974 | 1310.51658756 | 719.9997605860001 |
| otelcol typed | otelcol_process_uptime |  | 581.391542413 | 1301.391648391 | 720.000105978 |
| otelcol prod | otelcol_receiver_accepted_metric_points | prometheus_remote_write | 78340.0 | 233585.0 | 155245.0 |
| otelcol prod-contrib | otelcol_receiver_accepted_metric_points | prometheus_remote_write | 78512.0 | 233771.0 | 155259.0 |
| otelcol typed | otelcol_receiver_accepted_metric_points | prometheus_remote_write | 28606.0 | 64839.0 | 36233.0 |
| otelcol prod | otelcol_receiver_refused_metric_points | prometheus_remote_write | 0.0 | 0.0 | 0.0 |
| otelcol prod-contrib | otelcol_receiver_refused_metric_points | prometheus_remote_write | 0.0 | 0.0 | 0.0 |
| otelcol typed | otelcol_receiver_refused_metric_points | prometheus_remote_write | 0.0 | 0.0 | 0.0 |

## Sink (Prometheus with the OTLP receiver) vs the senders' TSDB, sample counts per metric family over the window

| sender | families | samples (source) | families equal | missing in sink | different | extra in sink | largest differences (sink - source) | missing | extra |
|---|---|---|---|---|---|---|---|---|---|
| prometheus-k8s-0 | 2783 | 10483618.0 | 2777 | 6 | 0 | 0 | {} | {"apiserver_request:burn2h": 0, "csv_abnormal": 0, "kube_job_complete": 0, "kube_job_spec_active_deadline_seconds": 0, "kube_job_status_completion_time": 0, "sum:apiserver_request:burnrate2h": 0} | {} |
| prometheus-k8s-1 | 2786 | 10485534.0 | 2778 | 8 | 0 | 0 | {} | {"apiserver_request:burn2h": 0, "csv_abnormal": 0, "kube_job_complete": 0, "kube_job_spec_active_deadline_seconds": 0, "kube_job_status_completion_time": 0, "kube_pod_container_status_waiting_reason": 0, "kube_pod_init_container_status_waiting_reason": 0, "sum:apiserver_request:burnrate2h": 0} | {} |
| typed job=prometheus | 379 | 48605.0 | 300 | 79 | 0 | 0 | {} | {"go_gc_duration_seconds": 240.0, "go_gc_duration_seconds_count": 48.0, "go_gc_duration_seconds_sum": 48.0, "go_gc_heap_allocs_by_size_bytes": 48.0, "go_gc_heap_frees_by_size_bytes": 48.0, "go_gc_pauses_seconds": 48.0, "go_sched_latencies_seconds": 48.0, "go_sched_pauses_stopping_gc_seconds": 48.0} | {} |
| typed job=avalanche | 23 | 31920.0 | 18 | 5 | 0 | 0 | {} | {"avalanche_histogram_metric_mmmmm_0_0": 960.0, "avalanche_histogram_metric_mmmmm_0_1": 960.0, "avalanche_summary_metric_mmmmm_0_0": 1920.0, "avalanche_summary_metric_mmmmm_0_0_count": 960.0, "avalanche_summary_metric_mmmmm_0_0_sum": 960.0} | {} |
| typed job=exemplar-app | 17 | 1541.0 | 13 | 4 | 0 | 0 | {} | {"corr_latency_seconds": 48.0, "corr_summary_seconds": 144.0, "corr_summary_seconds_count": 48.0, "corr_summary_seconds_sum": 48.0} | {} |
| typed job=stale-app | 16 | 814.0 | 10 | 6 | 0 | 0 | {} | {"corr_latency_seconds_bucket": 220.0, "corr_latency_seconds_count": 22.0, "corr_latency_seconds_sum": 22.0, "corr_summary_seconds": 66.0, "corr_summary_seconds_count": 22.0, "corr_summary_seconds_sum": 22.0} | {} |
| typed job=otelcol | 24 | 3840.0 | 24 | 0 | 0 | 0 | {} | {} | {} |

Typed families missing in the sink, classified: {"not emitted by the collector": 76, "emitted by the collector as a histogram, stored by the sink as classic series": 15}
- not emitted by the collector: avalanche_summary_metric_mmmmm_0_0, avalanche_summary_metric_mmmmm_0_0_count, avalanche_summary_metric_mmmmm_0_0_sum, corr_latency_seconds_bucket, corr_latency_seconds_count, corr_latency_seconds_sum, corr_summary_seconds, corr_summary_seconds_count, corr_summary_seconds_sum, go_gc_duration_seconds, go_gc_duration_seconds_count, go_gc_duration_seconds_sum, prometheus_engine_query_duration_histogram_seconds_bucket, prometheus_engine_query_duration_histogram_seconds_count, prometheus_engine_query_duration_histogram_seconds_sum, prometheus_engine_query_duration_seconds, prometheus_engine_query_duration_seconds_count, prometheus_engine_query_duration_seconds_sum, prometheus_http_request_duration_seconds_bucket, prometheus_http_request_duration_seconds_count, prometheus_http_request_duration_seconds_sum, prometheus_remote_storage_sent_batch_duration_seconds_bucket, prometheus_remote_storage_sent_batch_duration_seconds_count, prometheus_remote_storage_sent_batch_duration_seconds_sum, prometheus_rule_evaluation_duration_histogram_seconds_bucket, prometheus_rule_evaluation_duration_histogram_seconds_count, prometheus_rule_evaluation_duration_histogram_seconds_sum, prometheus_rule_evaluation_duration_seconds, prometheus_rule_evaluation_duration_seconds_count, prometheus_rule_evaluation_duration_seconds_sum, prometheus_rule_group_duration_histogram_seconds_bucket, prometheus_rule_group_duration_histogram_seconds_count, prometheus_rule_group_duration_histogram_seconds_sum, prometheus_rule_group_duration_seconds, prometheus_rule_group_duration_seconds_count, prometheus_rule_group_duration_seconds_sum, prometheus_sd_consul_rpc_duration_seconds, prometheus_sd_consul_rpc_duration_seconds_count, prometheus_sd_consul_rpc_duration_seconds_sum, prometheus_sd_file_scan_duration_seconds, prometheus_sd_file_scan_duration_seconds_count, prometheus_sd_file_scan_duration_seconds_sum, prometheus_sd_kuma_fetch_duration_seconds, prometheus_sd_kuma_fetch_duration_seconds_count, prometheus_sd_kuma_fetch_duration_seconds_sum, prometheus_target_interval_length_histogram_seconds_bucket, prometheus_target_interval_length_histogram_seconds_count, prometheus_target_interval_length_histogram_seconds_sum, prometheus_target_interval_length_seconds, prometheus_target_interval_length_seconds_count, prometheus_target_interval_length_seconds_sum, prometheus_target_sync_length_histogram_seconds_bucket, prometheus_target_sync_length_histogram_seconds_count, prometheus_target_sync_length_histogram_seconds_sum, prometheus_target_sync_length_seconds, prometheus_target_sync_length_seconds_count, prometheus_target_sync_length_seconds_sum, prometheus_tsdb_compaction_duration_seconds_bucket, prometheus_tsdb_compaction_duration_seconds_count, prometheus_tsdb_compaction_duration_seconds_sum, prometheus_tsdb_head_gc_duration_seconds_count, prometheus_tsdb_head_gc_duration_seconds_sum, prometheus_tsdb_sample_ooo_delta_bucket, prometheus_tsdb_sample_ooo_delta_count, prometheus_tsdb_sample_ooo_delta_sum, prometheus_tsdb_selected_series_compaction_duration_seconds_bucket, prometheus_tsdb_selected_series_compaction_duration_seconds_count, prometheus_tsdb_selected_series_compaction_duration_seconds_sum, prometheus_tsdb_stale_series_compaction_duration_seconds_bucket, prometheus_tsdb_stale_series_compaction_duration_seconds_count, prometheus_tsdb_stale_series_compaction_duration_seconds_sum, prometheus_tsdb_wal_fsync_duration_seconds, prometheus_tsdb_wal_fsync_duration_seconds_count, prometheus_tsdb_wal_fsync_duration_seconds_sum, prometheus_tsdb_wal_truncate_duration_seconds_count, prometheus_tsdb_wal_truncate_duration_seconds_sum
- emitted by the collector as a histogram, stored by the sink as classic series: avalanche_histogram_metric_mmmmm_0_0, avalanche_histogram_metric_mmmmm_0_1, corr_latency_seconds, go_gc_heap_allocs_by_size_bytes, go_gc_heap_frees_by_size_bytes, go_gc_pauses_seconds, go_sched_latencies_seconds, go_sched_pauses_stopping_gc_seconds, go_sched_pauses_stopping_other_seconds, go_sched_pauses_total_gc_seconds, go_sched_pauses_total_other_seconds, prometheus_http_response_size_bytes, prometheus_tsdb_compaction_chunk_range_seconds, prometheus_tsdb_compaction_chunk_samples, prometheus_tsdb_compaction_chunk_size_bytes
