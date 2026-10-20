# Remote write v2 from a Cluster Observability Operator MonitoringStack

Functional check for the reviewer question whether option 1 also covers a Prometheus managed by
the Cluster Observability Operator (COO): the `MonitoringStack` API passes the prometheus-operator
remote write spec through (`prometheusConfig.remoteWrite`, including `messageVersion`), so a
COO-managed Prometheus can send remote write v2 to the same collector. Like CMO, the MonitoringStack
API exposes neither `enableFeatures` nor the native histogram settings, so the metrics arrive untyped.

```bash
oc apply -f 00-coo-subscription.yaml          # COO from redhat-operators, namespace openshift-cluster-observability-operator
oc apply -f 01-monitoringstack.yaml           # MonitoringStack in otel-metrics-coo, remote write v2 to the collector
oc apply -f 02-sample-app.yaml                # avalanche sample app + ServiceMonitor selected by the stack
# verify: the stack's Prometheus has remoteWrite with messageVersion V2.0 and sends samples
oc get prometheus -n otel-metrics-coo -o jsonpath='{.items[0].spec.remoteWrite}'
scripts/pq.sh 'sum by (prometheus) (rate(prometheus_remote_storage_samples_total{remote_name="otel-collector"}[2m]))'
```

## Result (2026-10-20, OpenShift 5.0.0-0.nightly-2026-10-19 on AWS, COO 1.5.3)

The MonitoringStack reconciled (`ResourceDiscovery`, `Available`, `Reconciled` all true), the
generated `prometheus.monitoring.rhobs` CR carries `remoteWrite[0].messageVersion: V2.0` and no
`enableFeatures` or native histogram settings, and the instance sent the 165 avalanche series to
the collector with 1 shard and 0 failed samples (`prometheus_remote_storage_*` queried with
`promtool` inside the Prometheus pod). Same type limitation as CMO: no metadata, so the metrics
arrive as untyped gauges until the API exposes the Prometheus feature settings.
