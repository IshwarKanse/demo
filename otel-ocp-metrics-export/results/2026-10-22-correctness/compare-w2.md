# Window 2: (1792652704, 1792653244] = 9 min

## Typed path (Prometheus main with metadata -> contrib nightly receiver)

| float series / samples | count |
|---|---|
| samples_dump_matched_series | 23290 |
| samples_equal | 23290 |
| samples_source | 23290 |
| series_dump | 647 |
| series_exact | 647 |
| series_only_dump | 0 |
| series_only_source | 1065 |
| series_source | 1712 |

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
| corr_latency_seconds_bucket | 10 |
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
| corr_summary_seconds | 3 |
| prometheus_rule_evaluation_duration_seconds | 3 |
| prometheus_sd_file_scan_duration_seconds | 3 |
| prometheus_sd_kuma_fetch_duration_seconds | 3 |
| prometheus_tsdb_wal_fsync_duration_seconds | 3 |
| target_info | 3 |
| prometheus_sd_consul_rpc_duration_seconds_count | 2 |
| prometheus_sd_consul_rpc_duration_seconds_sum | 2 |
| corr_latency_seconds_count | 1 |

Series only in the dump (no TSDB counterpart), by family:

| family | series |
|---|---|

### Native histograms and NHCB

| histogram series / points | count |
|---|---|
| explicit_points | 2124 |
| exponential_points | 1692 |
| points_equal | 3816 |
| points_source | 3816 |
| series_dump | 106 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 106 |

NoRecordedValue flagged points in the dump: 0 on 0 series

## Production path, dump of `prod` (platform Prometheus 3.13.2, both replicas)

### replica prometheus-k8s-0

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 58204 |
| samples_equal | 58201 |
| samples_source | 58201 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="prometheus",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",image="quay.io/prometheus/prometheus:main",metrics_path="/metrics/cadvisor",name="k8s_prometheus_sink-prometheus-5c7d54db55-7rbb9_otel-correctness_UUID_0",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652771373]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-conmon-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",metrics_path="/metrics/cadvisor",node="node-3",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652771373]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652771373]
### replica prometheus-k8s-1

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 58198 |
| samples_equal | 58195 |
| samples_source | 58195 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="prometheus",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",image="quay.io/prometheus/prometheus:main",metrics_path="/metrics/cadvisor",name="k8s_prometheus_sink-prometheus-5c7d54db55-7rbb9_otel-correctness_UUID_0",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652793445]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-conmon-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",metrics_path="/metrics/cadvisor",node="node-3",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652793445]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652793445]

Metadata on the production path (kind, prometheus.type, unit, has description -> families): {"('gauge', 'unknown', '', False)": 31}
Points with startTimeUnixNano: 0 of 583928
Points with an empty resource (no job/instance, e.g. ALERTS): 252
Resource splits (job/instance pairs seen with more than one resource attribute set): 0 of 154 pairs
Scopes: {"('Red Hat build of OpenTelemetry', '0.158.0')": 63673}

## Production path, dump of `prod-contrib` (platform Prometheus 3.13.2, both replicas)

### replica prometheus-k8s-0

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 58204 |
| samples_equal | 58201 |
| samples_source | 58201 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="prometheus",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",image="quay.io/prometheus/prometheus:main",metrics_path="/metrics/cadvisor",name="k8s_prometheus_sink-prometheus-5c7d54db55-7rbb9_otel-correctness_UUID_0",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652771373]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-conmon-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",metrics_path="/metrics/cadvisor",node="node-3",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652771373]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652771373]
### replica prometheus-k8s-1

| float series / samples | count |
|---|---|
| extra_nan_in_dump | 3 |
| points_without_replica_label | 0 |
| samples_dump_matched_series | 58198 |
| samples_equal | 58195 |
| samples_source | 58195 |
| series_dump | 2986 |
| series_exact | 2986 |
| series_only_dump | 0 |
| series_only_source | 0 |
| series_source | 2986 |

Examples `extra_nan_in_dump`:
- container_cpu_usage_seconds_total{container="prometheus",cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",image="quay.io/prometheus/prometheus:main",metrics_path="/metrics/cadvisor",name="k8s_prometheus_sink-prometheus-5c7d54db55-7rbb9_otel-correctness_UUID_0",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652793445]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice/crio-conmon-6adf8fbe8b0496110c7f8009e53edb6a5a67ecd7989725e5e4e6f4f8465e6246.scope",metrics_path="/metrics/cadvisor",node="node-3",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652793445]
- container_cpu_usage_seconds_total{cpu="total",endpoint="https-metrics",id="/kubepods.slice/kubepods-burstable.slice/kubepods-burstable-podfb0f1f12_818b_4cb8_8369_083096bd577b.slice",metrics_path="/metrics/cadvisor",namespace="otel-correctness",node="node-3",pod="sink-prometheus-5c7d54db55-7rbb9",service="kubelet"} instance=IP-5:10250 job=kubelet [1792652793445]

Metadata on the production path (kind, prometheus.type, unit, has description -> families): {"('gauge', 'unknown', '', False)": 31}
Points with startTimeUnixNano: 0 of 643774
Points with an empty resource (no job/instance, e.g. ALERTS): 252
Resource splits (job/instance pairs seen with more than one resource attribute set): 0 of 154 pairs
Scopes: {"('OpenTelemetry Collector Contrib', '0.163.1')": 48249}

Typed path resource pairs: 7, splits: 0; extra resource attributes seen: ["service_instance_id", "service_name", "service_version"]

## Counters at the window boundaries (value at start, at end, delta)

| where | metric | name | start | end | delta |
|---|---|---|---|---|---|
| typed | prometheus_remote_storage_exemplars_failed_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_exemplars_total | typed | 500.0 | 644.0 | 144.0 |
| typed | prometheus_remote_storage_histograms_failed_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_histograms_pending | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_histograms_retried_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_histograms_total | typed | 8709.0 | 12525.0 | 3816.0 |
| typed | prometheus_remote_storage_samples_failed_total | typed | 87493.0 | 125725.0 | 38232.0 |
| typed | prometheus_remote_storage_samples_pending | typed | 25.0 | 0.0 | -25.0 |
| typed | prometheus_remote_storage_samples_retried_total | typed | 0.0 | 0.0 | 0.0 |
| typed | prometheus_remote_storage_samples_total | typed | 143387.0 | 205041.0 | 61654.0 |
| typed | prometheus_remote_storage_sent_batch_duration_seconds_count | typed | 258.0 | 366.0 | 108.0 |
| typed | prometheus_remote_storage_shards | typed | 1.0 | 1.0 | 0.0 |
| typed | prometheus_tsdb_head_samples_appended_total |  | 144392.0 | 206021.0 | 61629.0 |
| typed | prometheus_tsdb_head_samples_appended_total |  | 8786.0 | 12602.0 | 3816.0 |
| typed | prometheus_tsdb_head_series |  | 1843.0 | 1844.0 | 1.0 |
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
| prod0 | prometheus_remote_storage_samples_pending | prod | 281.0 | 1557.0 | 1276.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod-contrib | 281.0 | 377.0 | 96.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod | 548.0 | 357.0 | -191.0 |
| prod0 | prometheus_remote_storage_samples_pending | prod-contrib | 548.0 | 906.0 | 358.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 8000.0 | 8000.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 8000.0 | 8000.0 |
| prod0 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_remote_storage_samples_total | prod | 15498000.0 | 23378811.0 | 7880811.0 |
| prod0 | prometheus_remote_storage_samples_total | prod-contrib | 15498000.0 | 23372000.0 | 7874000.0 |
| prod0 | prometheus_remote_storage_samples_total | prod | 15456000.0 | 23336549.0 | 7880549.0 |
| prod0 | prometheus_remote_storage_samples_total | prod-contrib | 15456000.0 | 23328000.0 | 7872000.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 7749.0 | 11730.0 | 3981.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 7749.0 | 11686.0 | 3937.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 7728.0 | 11686.0 | 3958.0 |
| prod0 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 7728.0 | 11664.0 | 3936.0 |
| prod0 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 141441618.0 | 149315714.0 | 7874096.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 141655709.0 | 149528067.0 | 7872358.0 |
| prod0 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod0 | prometheus_tsdb_head_series |  | 498588.0 | 443902.0 | -54686.0 |
| prod0 | prometheus_tsdb_head_series |  | 495786.0 | 444018.0 | -51768.0 |
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
| prod1 | prometheus_remote_storage_samples_pending | prod | 580.0 | 262.0 | -318.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod-contrib | 580.0 | 1073.0 | 493.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod | 518.0 | 327.0 | -191.0 |
| prod1 | prometheus_remote_storage_samples_pending | prod-contrib | 518.0 | 876.0 | 358.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 8000.0 | 8000.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod | 0.0 | 8000.0 | 8000.0 |
| prod1 | prometheus_remote_storage_samples_retried_total | prod-contrib | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_remote_storage_samples_total | prod | 15662000.0 | 23542811.0 | 7880811.0 |
| prod1 | prometheus_remote_storage_samples_total | prod-contrib | 15662000.0 | 23534000.0 | 7872000.0 |
| prod1 | prometheus_remote_storage_samples_total | prod | 15466000.0 | 23346549.0 | 7880549.0 |
| prod1 | prometheus_remote_storage_samples_total | prod-contrib | 15466000.0 | 23338000.0 | 7872000.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 7831.0 | 11812.0 | 3981.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 7831.0 | 11767.0 | 3936.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod | 7733.0 | 11691.0 | 3958.0 |
| prod1 | prometheus_remote_storage_sent_batch_duration_seconds_count | prod-contrib | 7733.0 | 11669.0 | 3936.0 |
| prod1 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_remote_storage_shards | prod | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_remote_storage_shards | prod-contrib | 1.0 | 1.0 | 0.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 141605917.0 | 149478410.0 | 7872493.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 141665679.0 | 149538037.0 | 7872358.0 |
| prod1 | prometheus_tsdb_head_samples_appended_total |  | 0.0 | 0.0 | 0.0 |
| prod1 | prometheus_tsdb_head_series |  | 498588.0 | 443903.0 | -54685.0 |
| prod1 | prometheus_tsdb_head_series |  | 495786.0 | 444018.0 | -51768.0 |
| otelcol prod | otelcol_exporter_enqueue_failed_metric_points | otlphttp | None | 16000.0 | None |
| otelcol prod | otelcol_exporter_queue_size | otlphttp | 2000.0 | 2000.0 | 0.0 |
| otelcol typed | otelcol_exporter_queue_size | otlphttp | 0.0 | 0.0 | 0.0 |
| otelcol prod | otelcol_exporter_sent_metric_points | file | 233585.0 | 349943.0 | 116358.0 |
| otelcol prod-contrib | otelcol_exporter_sent_metric_points | file | 233771.0 | 350116.0 | 116345.0 |
| otelcol typed | otelcol_exporter_sent_metric_points | file | 64839.0 | 91944.0 | 27105.0 |
| otelcol prod | otelcol_exporter_sent_metric_points | otlphttp | 31568000.0 | 47313360.0 | 15745360.0 |
| otelcol typed | otelcol_exporter_sent_metric_points | otlphttp | 64839.0 | 91944.0 | 27105.0 |
| otelcol prod | otelcol_process_memory_rss |  | 154230784.0 | 175636480.0 | 21405696.0 |
| otelcol prod-contrib | otelcol_process_memory_rss |  | 251461632.0 | 251604992.0 | 143360.0 |
| otelcol typed | otelcol_process_memory_rss |  | 248528896.0 | 248938496.0 | 409600.0 |
| otelcol prod | otelcol_process_uptime |  | 1307.544863238 | 1847.544240295 | 539.999377057 |
| otelcol prod-contrib | otelcol_process_uptime |  | 1310.51658756 | 1850.516708561 | 540.000121001 |
| otelcol typed | otelcol_process_uptime |  | 1301.391648391 | 1841.391806487 | 540.000158096 |
| otelcol prod | otelcol_receiver_accepted_metric_points | prometheus_remote_write | 233585.0 | 349943.0 | 116358.0 |
| otelcol prod-contrib | otelcol_receiver_accepted_metric_points | prometheus_remote_write | 233771.0 | 350116.0 | 116345.0 |
| otelcol typed | otelcol_receiver_accepted_metric_points | prometheus_remote_write | 64839.0 | 91944.0 | 27105.0 |
| otelcol prod | otelcol_receiver_refused_metric_points | prometheus_remote_write | 0.0 | 0.0 | 0.0 |
| otelcol prod-contrib | otelcol_receiver_refused_metric_points | prometheus_remote_write | 0.0 | 0.0 | 0.0 |
| otelcol typed | otelcol_receiver_refused_metric_points | prometheus_remote_write | 0.0 | 0.0 | 0.0 |

## Sink (Prometheus with the OTLP receiver) vs the senders' TSDB, sample counts per metric family over the window

| sender | families | samples (source) | families equal | missing in sink | different | extra in sink | largest differences (sink - source) | missing | extra |
|---|---|---|---|---|---|---|---|---|---|
| prometheus-k8s-0 | 2783 | 7872449.0 | 2777 | 6 | 0 | 0 | {} | {"apiserver_request:burn2h": 0, "csv_abnormal": 0, "kube_job_complete": 0, "kube_job_spec_active_deadline_seconds": 0, "kube_job_status_completion_time": 0, "sum:apiserver_request:burnrate2h": 0} | {} |
| prometheus-k8s-1 | 2786 | 7873078.0 | 2777 | 9 | 0 | 0 | {} | {"apiserver_request:burn2h": 0, "csv_abnormal": 0, "kube_job_complete": 0, "kube_job_spec_active_deadline_seconds": 0, "kube_job_status_completion_time": 0, "kube_pod_container_status_waiting_reason": 0, "kube_pod_deletion_timestamp": 0, "kube_pod_init_container_status_waiting_reason": 0} | {} |
| typed job=prometheus | 379 | 37260.0 | 300 | 79 | 0 | 0 | {} | {"go_gc_duration_seconds": 180.0, "go_gc_duration_seconds_count": 36.0, "go_gc_duration_seconds_sum": 36.0, "go_gc_heap_allocs_by_size_bytes": 36.0, "go_gc_heap_frees_by_size_bytes": 36.0, "go_gc_pauses_seconds": 36.0, "go_sched_latencies_seconds": 36.0, "go_sched_pauses_stopping_gc_seconds": 36.0} | {} |
| typed job=avalanche | 23 | 23940.0 | 18 | 5 | 0 | 0 | {} | {"avalanche_histogram_metric_mmmmm_0_0": 720.0, "avalanche_histogram_metric_mmmmm_0_1": 720.0, "avalanche_summary_metric_mmmmm_0_0": 1440.0, "avalanche_summary_metric_mmmmm_0_0_count": 720.0, "avalanche_summary_metric_mmmmm_0_0_sum": 720.0} | {} |
| typed job=exemplar-app | 17 | 1156.0 | 13 | 4 | 0 | 0 | {} | {"corr_latency_seconds": 36.0, "corr_summary_seconds": 108.0, "corr_summary_seconds_count": 36.0, "corr_summary_seconds_sum": 36.0} | {} |
| typed job=stale-app | 5 | 180.0 | 5 | 0 | 0 | 0 | {} | {} | {} |
| typed job=otelcol | 25 | 2910.0 | 25 | 0 | 0 | 0 | {} | {} | {} |

Typed families missing in the sink, classified: {"not emitted by the collector": 73, "emitted by the collector as a histogram, stored by the sink as classic series": 15}
- not emitted by the collector: avalanche_summary_metric_mmmmm_0_0, avalanche_summary_metric_mmmmm_0_0_count, avalanche_summary_metric_mmmmm_0_0_sum, corr_summary_seconds, corr_summary_seconds_count, corr_summary_seconds_sum, go_gc_duration_seconds, go_gc_duration_seconds_count, go_gc_duration_seconds_sum, prometheus_engine_query_duration_histogram_seconds_bucket, prometheus_engine_query_duration_histogram_seconds_count, prometheus_engine_query_duration_histogram_seconds_sum, prometheus_engine_query_duration_seconds, prometheus_engine_query_duration_seconds_count, prometheus_engine_query_duration_seconds_sum, prometheus_http_request_duration_seconds_bucket, prometheus_http_request_duration_seconds_count, prometheus_http_request_duration_seconds_sum, prometheus_remote_storage_sent_batch_duration_seconds_bucket, prometheus_remote_storage_sent_batch_duration_seconds_count, prometheus_remote_storage_sent_batch_duration_seconds_sum, prometheus_rule_evaluation_duration_histogram_seconds_bucket, prometheus_rule_evaluation_duration_histogram_seconds_count, prometheus_rule_evaluation_duration_histogram_seconds_sum, prometheus_rule_evaluation_duration_seconds, prometheus_rule_evaluation_duration_seconds_count, prometheus_rule_evaluation_duration_seconds_sum, prometheus_rule_group_duration_histogram_seconds_bucket, prometheus_rule_group_duration_histogram_seconds_count, prometheus_rule_group_duration_histogram_seconds_sum, prometheus_rule_group_duration_seconds, prometheus_rule_group_duration_seconds_count, prometheus_rule_group_duration_seconds_sum, prometheus_sd_consul_rpc_duration_seconds, prometheus_sd_consul_rpc_duration_seconds_count, prometheus_sd_consul_rpc_duration_seconds_sum, prometheus_sd_file_scan_duration_seconds, prometheus_sd_file_scan_duration_seconds_count, prometheus_sd_file_scan_duration_seconds_sum, prometheus_sd_kuma_fetch_duration_seconds, prometheus_sd_kuma_fetch_duration_seconds_count, prometheus_sd_kuma_fetch_duration_seconds_sum, prometheus_target_interval_length_histogram_seconds_bucket, prometheus_target_interval_length_histogram_seconds_count, prometheus_target_interval_length_histogram_seconds_sum, prometheus_target_interval_length_seconds, prometheus_target_interval_length_seconds_count, prometheus_target_interval_length_seconds_sum, prometheus_target_sync_length_histogram_seconds_bucket, prometheus_target_sync_length_histogram_seconds_count, prometheus_target_sync_length_histogram_seconds_sum, prometheus_target_sync_length_seconds, prometheus_target_sync_length_seconds_count, prometheus_target_sync_length_seconds_sum, prometheus_tsdb_compaction_duration_seconds_bucket, prometheus_tsdb_compaction_duration_seconds_count, prometheus_tsdb_compaction_duration_seconds_sum, prometheus_tsdb_head_gc_duration_seconds_count, prometheus_tsdb_head_gc_duration_seconds_sum, prometheus_tsdb_sample_ooo_delta_bucket, prometheus_tsdb_sample_ooo_delta_count, prometheus_tsdb_sample_ooo_delta_sum, prometheus_tsdb_selected_series_compaction_duration_seconds_bucket, prometheus_tsdb_selected_series_compaction_duration_seconds_count, prometheus_tsdb_selected_series_compaction_duration_seconds_sum, prometheus_tsdb_stale_series_compaction_duration_seconds_bucket, prometheus_tsdb_stale_series_compaction_duration_seconds_count, prometheus_tsdb_stale_series_compaction_duration_seconds_sum, prometheus_tsdb_wal_fsync_duration_seconds, prometheus_tsdb_wal_fsync_duration_seconds_count, prometheus_tsdb_wal_fsync_duration_seconds_sum, prometheus_tsdb_wal_truncate_duration_seconds_count, prometheus_tsdb_wal_truncate_duration_seconds_sum
- emitted by the collector as a histogram, stored by the sink as classic series: avalanche_histogram_metric_mmmmm_0_0, avalanche_histogram_metric_mmmmm_0_1, corr_latency_seconds, go_gc_heap_allocs_by_size_bytes, go_gc_heap_frees_by_size_bytes, go_gc_pauses_seconds, go_sched_latencies_seconds, go_sched_pauses_stopping_gc_seconds, go_sched_pauses_stopping_other_seconds, go_sched_pauses_total_gc_seconds, go_sched_pauses_total_other_seconds, prometheus_http_response_size_bytes, prometheus_tsdb_compaction_chunk_range_seconds, prometheus_tsdb_compaction_chunk_samples, prometheus_tsdb_compaction_chunk_size_bytes
