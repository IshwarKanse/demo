# Data correctness of the `prometheus_remote_write` receiver (remote write v2), 2026-10-22

OpenShift 5.0.0-0.nightly-2026-10-21 on AWS (3 control plane, 3 worker nodes), platform Prometheus
3.13.2 (two replicas, 152 to 154 job/instance pairs, about 490,000 series each), Red Hat build of
OpenTelemetry 0.158.0 (operator from the Red Hat Operators catalog), contrib nightly
`0.164.0-nightly.29f43fe`, Prometheus `main` of 2026-10-21 as the typed sender and as the OTLP sink.
Setup and method in [`README.md`](./README.md); timeline in [`timeline.txt`](./timeline.txt).

Window 1: 12 minutes of steady state, 06:53:04 to 07:05:04 UTC (the stale target scaled to 0 at
06:58:06). Window 2: 9 minutes, 07:05:04 to 07:14:04, with the OTLP sink scaled to 0 from 07:06:06
to 07:08:09.

## Verdict

**The collector emits an exact, complete, exactly-once copy of every sample Prometheus writes:**
same value, same millisecond timestamp, same labels, every series, both replicas, on the product
collector 0.158.0 and on the newest upstream receiver, in steady state and through a 2 minute
backend outage with replay. What differs is representation, not data:

1. On the production path (OpenShift Prometheus 3.13.2) every family arrives as an untyped gauge
   without unit, help or start timestamp (no metadata WAL records in Prometheus 3.10 to 3.15,
   prometheus/prometheus#20094, fix prometheus/prometheus#19678 on main only).
2. On a typed sender, classic histogram `_bucket`/`_sum`/`_count` series and summary series are
   dropped and counted as failed samples (62% of the samples of the typed sender here);
   native histograms and NHCB arrive exactly (opentelemetry-collector-contrib#52224, fix PR
   opentelemetry-collector-contrib#52252 open).
3. Staleness markers arrive as ordinary NaN data points without the OTLP no-recorded-value flag.
4. No start timestamps: the remote write v2 `created_timestamp` is empty even with
   `created-timestamp-zero-ingestion`, so counters are cumulative sums without a start time and a
   reset is only visible as the value drop.
5. Mapping, as the OpenTelemetry compatibility specification prescribes: `job` → `service.name`,
   `instance` → `service.instance.id`, `target_info` labels → resource attributes (`target_info`
   itself is not emitted), all other labels including the external labels `prometheus` and
   `prometheus_replica` → data point attributes, series without job and instance (`ALERTS`) →
   empty resource, scope = the collector's build info, units converted to UCUM (`seconds` → `s`,
   `bytes` → `By`, `celsius` → `Cel`), metric names unchanged (`_total` kept).
6. Every sample arrives twice, once per platform replica, distinguished by `prometheus_replica`.

## Results

| Check | How it was measured | Expected | Observed | Verdict |
|---|---|---|---|---|
| Completeness, production path, whole stream | Sender counters at the window boundaries; sample counts per metric family over the window in each replica's TSDB (2,783 and 2,786 families) against the sink | every sample sent is stored once in the sink | window 1: 10,486,000 samples sent per replica to each collector, 0 failed, 0 dropped, 0 retried; sink = TSDB for all 2,777 families with samples (10,483,618 and 10,485,534 samples; the remote write counter is within one 2,000-sample batch of the TSDB count, which does not contain staleness markers). Window 2 (outage): sink = TSDB again, 7,872,449 and 7,873,078 samples. The exporter sent 20,968,000 points in window 1 = both replicas' counters within one batch. | pass |
| Completeness, production path, per series | Raw samples of 15 metric families (2,986 series per replica: `up`, `scrape_samples_scraped`, `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, `node_network_receive_bytes_total`, `etcd_disk_wal_fsync_duration_seconds*`, `prometheus_tsdb_head_series`, `prometheus_remote_storage_*`, `kube_node_status_condition`, `kubelet_running_pods`, `go_gc_duration_seconds*`, `container_cpu_usage_seconds_total`, `ALERTS`) from each replica's TSDB against the file exporter dump of the product collector and of the contrib nightly | every (series, timestamp, value) once | window 1: 77,609 + 77,618 samples, 2,986 + 2,986 series, all exact, 0 missing, 0 duplicates, 0 value differences, 0 series only on one side; window 2: 58,201 + 58,195 samples, all exact. Both collectors identical. | pass |
| Completeness, typed path | Every raw sample of the typed sender (1,737 float series, 106 histogram series) against the complete dump | every series the receiver supports, once | 655 float series / 31,213 samples exact, 106 histogram series / 5,002 points exact; emitted points 36,224 = 81,747 samples sent − 50,372 counted failed − 144 `target_info` samples + 5,000 histograms (36,231, boundary skew 7). 1,082 series not emitted: classic `_bucket`/`_sum`/`_count` (dropped), summaries (dropped), `target_info` (3 series, consumed into resources). Window 2: 23,290 + 3,816 points exact. | pass, with the known drops |
| Values and timestamps | Per-sample equality of value and millisecond timestamp (the dump timestamp is the Prometheus timestamp × 10⁶ ns); NaN, +Inf, −Inf gauges; a counter resetting every 150 s; a target scaled to 0 inside the window | identical values and timestamps; resets visible; staleness carried | all compared samples equal (189,000 in window 1, 143,500 in window 2); NaN, +Inf and −Inf preserved (`"NaN"`, `"Infinity"`, `"-Infinity"` in the JSON dump); the reset is the value drop, no start timestamp; staleness markers arrive as NaN points: 9 on the typed path (every float series of the stale target, at the next scrape timestamp) and 3 per replica and window on the production path (the stale target's cAdvisor series), none with the no-recorded-value flag, so they cannot be told from a NaN value in the export | pass; staleness = NaN point |
| Labels and names | Series identity match (name + every label) between source and dump; a label value with `"`, `\`, newline, tab, `ü` and `日本`; resource and scope attributes in the dump | names and labels unchanged; job/instance as resource attributes | 100% of the series matched on name and full label set, `_total` kept, the escaped label value identical; `job` → `service.name`, `instance` → `service.instance.id`; `target_info` labels → resource attributes (the collectors' own telemetry contributed `service_name`, `service_version`, `service_instance_id`), `target_info` not emitted; `prometheus`, `prometheus_replica` and all other labels → data point attributes; `ALERTS` (no job/instance) → empty resource, 336 points; scope `Red Hat build of OpenTelemetry 0.158.0` / `OpenTelemetry Collector Contrib 0.163.1` (receiver build info, no `otel_scope_*` labels) | pass |
| Metadata, typed path | Prometheus `/api/v1/metadata` type, unit and help against metric kind, monotonic flag, `prometheus.type` metadata, unit and description in the dump; `startTimeUnixNano` presence | type, unit and help carried; start timestamps from created timestamps | 153 counter families → cumulative monotonic Sum (`prometheus.type=counter`), 121 gauge → Gauge, 15 histogram → Histogram (NHCB), 15 histogram → ExponentialHistogram (native), info → non-monotonic Sum (`prometheus.type=info`), `up`/`scrape_*` (no type) → Gauge with `prometheus.type=unknown`; summaries dropped. Units: `seconds` → `s`, `bytes` → `By`, `celsius` → `Cel`, `requests`/`samples`/`series`/`targets` unchanged. Help → description. Start timestamps on 0 of 178,550 points, although `created-timestamp-zero-ingestion` was on and the exposition carried `_created`: Prometheus forwards the WAL sample's start timestamp (`storage/remote/queue_manager.go`), and the WAL samples carry none. | pass; no start timestamps |
| Metadata, production path | Same, on the platform stream | n/a (known gap) | 31 of 31 dumped families: Gauge, `prometheus.type=unknown`, empty unit and description, no start timestamp, on both collectors | known gap (prometheus/prometheus#20094) |
| Native histograms and NHCB, typed path | Per data point: count, sum and every bucket derived from the exponential schema (scale, offset, bucket counts, zero threshold) or from the custom bounds, against the source histogram buckets; classic series counted | native and NHCB exact; classic series dropped and counted as failed | 2,213 exponential points (avalanche native histogram schema 3 → scale 3, zero threshold 2.9e-39; `prometheus_http_request_duration_seconds`) and 2,789 NHCB points (15 families, custom values → `explicitBounds`) all equal in count, sum and buckets, 0 mismatches. Classic series dropped: 1,079 `_bucket`/`_sum`/`_count` and summary series; a classic histogram scraped without NHCB conversion (`corr_latency_seconds` of the stale target) is lost entirely. 50,372 of 81,747 samples (62%) counted failed in `prometheus_remote_storage_samples_failed_total`, 26 "statistics indicate some data was not written" errors in the sender log, 0 histograms failed. | pass for native/NHCB; known drop (contrib#52224, PR #52252) |
| Exemplars, typed path | `query_exemplars` of the sender against the exemplars on the dumped data points, matched on trace id, span id, value, timestamp and the other labels | attached to the right data point with ids and timestamp | window 1: 96 of 96 histogram exemplars (on the NHCB data points of `corr_latency_seconds`), 48 + 48 of 48 + 48 counter exemplars on the exemplar app and 22 + 22 on the stale target, all equal; `trace_id`/`span_id` → `traceId`/`spanId`, the extra `user_id` label → `filteredAttributes`; `prometheus_remote_storage_exemplars_total` 284 sent, 0 failed. Exemplars on dropped classic buckets (job without NHCB conversion) are lost with the series (22 + 22). | pass |
| Resource splitting above 1000 job/instance pairs | job/instance pairs seen with more than one resource attribute set, in all three dumps | none below the limit | 154 pairs on the platform stream, 7 on the typed stream, 0 splits. Above the limit: the 2026-10-22 end-to-end run of contrib#52195 (1,200 pairs, 16,835 samples) showed 800 pairs split between an enriched and a bare resource and no sample lost; `resource_cache_size` (PR #52248) and the eviction counter (PR #52249) are open. | pass (referenced) |
| Ordering and backend outage replay | Sink scaled to 0 for 2 minutes inside window 2; per-series comparison over the window; collector queue, sender retries and rejections from the counters and logs | replayed samples identical and complete, no duplicates, no loss | queue full at 100,000 items for 2.3 minutes; the receiver blocked and 8 sender requests hit the 30 s remote write timeout (`context canceled`, 16,000 points rejected by the exporter, `samples_retried_total` 8,000 per replica, 0 failed, 0 refused); replay burst up to 2.2 million points per 15 s, backlog drained 50 s after the sink came back; per series 0 missing, 0 duplicates, 0 differences (116,396 production samples, 27,106 typed points), sink = TSDB per family | pass |

Both production collectors (product 0.158.0 and contrib nightly 0.164) produced identical results; only the scope name differs.

## What differs and why

- **Everything untyped on the production path.** Prometheus 3.10 to 3.15 write no metadata WAL records, so remote write v2 carries `METRIC_TYPE_UNSPECIFIED` with empty unit and help and the receiver emits a Gauge with `prometheus.type=unknown`. prometheus/prometheus#20094 (backport request), fix prometheus/prometheus#19678 on main; CMO settings in MON-4412.
- **Classic histogram and summary series dropped when typed.** The receiver skips `HISTOGRAM`-typed series that carry float samples and all `SUMMARY` series and reports them as not written, so the sender counts them failed and `PrometheusRemoteStorageFailures` fires; a histogram scraped without NHCB conversion disappears with its exemplars. opentelemetry-collector-contrib#52224; fix PR opentelemetry-collector-contrib#52252 (counts them as written; the series stay unexported).
- **Staleness markers as NaN points.** The receiver copies float samples unchanged (`addNumberDatapoints`), so the stale NaN becomes a NaN data point without `NO_RECORDED_VALUE`; only stale native histograms get the flag (`addExponentialHistogramDatapoint`). A backend sees a NaN value instead of an end-of-series mark. Not tracked upstream yet.
- **No start timestamps.** Prometheus `main` fills `created_timestamp` from the WAL sample's start timestamp, which is empty for scraped samples even with `created-timestamp-zero-ingestion`; the receiver maps it to `startTimeUnixNano` only when present. Counters arrive without a start time.
- **`otelcol_receiver_accepted_metric_points` is not a completeness counter on this harness.** With a second pipeline that filters, the receiver counts the data points left after the fanout hands the original data to the mutating pipeline (155,245 instead of about 21 million in window 1); the exporter's `otelcol_exporter_sent_metric_points` and the sender counters were used instead. A production collector with a single pipeline is not affected.
- **Mapping and duplication.** The job/instance/`target_info`/scope mapping and the UCUM unit conversion follow the OpenTelemetry Prometheus compatibility specification; both platform replicas send every sample, deduplication belongs to the backend (`prometheus_replica`).

## Not measured

- Staleness of native histograms (the stale target had no native or NHCB series), so the `NO_RECORDED_VALUE` flag path was not exercised.
- Resource splitting above 1,000 job/instance pairs on this cluster (154 pairs); the earlier 1,200-pair measurement is referenced instead.
- Series with a `namespace/name` job label (`service.namespace` split) and `otel_scope_*` labels: none on either stream.
