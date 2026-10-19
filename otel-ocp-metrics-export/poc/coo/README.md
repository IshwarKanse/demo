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
