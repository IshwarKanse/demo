Cluster: OpenShift 5.0.0-0.nightly-2026-10-19-060022 on AWS, 7 nodes. Collector image: registry.redhat.io/rhosdt/opentelemetry-collector-rhel9@sha256:af76e9b5eaa89400714f189c0bf94026e41bd3476920d4dd961ac217fff4630a.

Objects: stored = sum over the resources of apiserver_storage_objects; watched = the stored objects of the kinds the client has an informer for (the collector: pods, namespaces, deployments, replica sets, services, jobs, cron jobs, HPAs, quotas, cluster resource quotas; kube-state-metrics: those plus config maps, secrets and endpoints). Steady values are averages over the 20 min steady window, max values the maximum over all phases of the step. Inventory times: seconds after the loader ended (create) or after the pod start (restart) until the client reported every deployment of the inventory, 30 s intervals and 5 to 10 s polling. LIST rows come from the audit log of the restart windows. Points per cycle: the receiver's accepted points per 30 s cycle (rate x 30) against the points the inventory should produce (the empty-inventory rate plus 2 per deployment and replica set, 5 per job, 1 per cron job, 4 per HPA, 2 per quota, 1 per namespace): 100 % means the receiver keeps its interval.

| step | objects stored / watched by collector / by kube-state-metrics | loader s | collector CPU avg / churn p95 | collector WSS MiB avg / max | collector RSS MiB max | collector points/s | points per cycle measured / expected | refused pts/s | collector restarts (OOM) | kube-state-metrics CPU avg / churn p95 | kube-state-metrics WSS MiB avg / max | kube-state-metrics RSS MiB max | samples per scrape / scrape s max | inventory after create: collector / ksm | inventory after restart: collector / ksm | collector LISTs (count, sum s, longest) | kube-state-metrics LISTs (count, sum s, longest) | kube-apiserver CPU steady / peak at restarts | kube-apiserver WSS GiB max | etcd db MiB / fsync p99 s | LIST/s all clients |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0k | 22,076 / 1,337 / 3,504 | 0 | 0.001 / 0.000 | 68 / 68 | 157 | 119 | 3,577 / 3,577 (100 %) | 0 | 0 (no) | 0.002 / 0.000 | 164 / 168 | 152 | 23,583 / 0.1 | - / - | - / - | - | - | 0.87 / 0.00 | 2.7 | 70 / 0.004 | 0.4 |
| 10k | 21,260 / 5,992 / 15,103 | 21 | 0.003 / 0.005 | 124 / 131 | 210 | 470 | 14,100 / 12,699 (111 %) | 0 | 0 (no) | 0.002 / 0.004 | 174 / 211 | 240 | 86,189 / 0.2 | 5 / 0 | 35 / 45 | 14 (watch+initial), 0.0 s, clusterresourcequotas 0.00 s | 59 (watch+initial), 3.8 s, configmaps 0.29 s | 0.82 / 1.33 | 3.2 | 109 / 0.004 | 0.2 |
| 50k | 78,257 / 25,480 / 65,311 | 57 | 0.010 / 0.017 | 308 / 317 | 367 | 1,719 | 51,575 / 48,438 (106 %) | 0 | 0 (no) | 0.006 / 0.013 | 249 / 568 | 498 | 320,947 / 0.8 | 0 / 25 | 35 / 35 | 14 (watch+initial), 0.5 s, services 0.37 s | 59 (watch+initial), 13.9 s, configmaps 1.19 s | 0.82 / 1.28 | 3.8 | 267 / 0.004 | 0.2 |
| 100k | 147,283 / 49,834 / 128,065 | 157 | 0.020 / 0.030 | 572 / 594 | 566 | 3,278 | 98,345 / 93,098 (106 %) | 0 | 0 (no) | 0.012 / 0.022 | 517 / 963 | 782 | 614,339 / 1.7 | 10 / 0 | 36 / 35 | 14 (watch+initial), 3.5 s, replicasets 1.01 s | 59 (watch+initial), 19.2 s, configmaps 1.83 s | 1.18 / 2.12 | 5.3 | 419 / 0.004 | 0.2 |

Linear fits over the steps (per watched object of each client):
- collector working set, steady: 56 MiB + 1028 MiB per 100,000 watched objects
- collector RSS, max over the step: 153 MiB + 831 MiB per 100,000 watched objects
- kube-state-metrics working set, steady: 127 MiB + 281 MiB per 100,000 watched objects
- kube-state-metrics RSS, max over the step: 153 MiB + 499 MiB per 100,000 watched objects

Start-up requests per resource in the restart windows (audit log; a LIST has its duration from the audit event, an initial-events watch (client-go watch list) its streaming duration from apiserver_watch_list_duration_seconds and no response size):

| step | client | resource | requests | kind | longest s | mean bytes per LIST of any client in the window (apiserver_response_sizes; a watch-list stream has no size metric) |
|---|---|---|---|---|---|---|
| 10k | collector | clusterresourcequotas | 1 | watch+initial | 0.00 | 0 |
| 10k | collector | cronjobs | 1 | watch+initial | 0.00 | 0 |
| 10k | collector | daemonsets | 1 | watch+initial | 0.00 | 0 |
| 10k | collector | deployments | 1 | watch+initial | 0.00 | 4,731 |
| 10k | collector | horizontalpodautoscalers | 1 | watch+initial | 0.00 | 0 |
| 10k | collector | jobs | 1 | watch+initial | 0.00 | 0 |
| 10k | collector | namespaces | 1 | watch+initial | 0.00 | 0 |
| 10k | collector | nodes | 1 | watch+initial | 0.00 | 102,453 |
| 10k | kube-state-metrics | configmaps | 2 | watch+initial | 0.29 | 29,264 |
| 10k | kube-state-metrics | secrets | 2 | watch+initial | 0.28 | 19,682 |
| 10k | kube-state-metrics | services | 2 | watch+initial | 0.25 | 900,968 |
| 10k | kube-state-metrics | replicasets | 2 | watch+initial | 0.25 | 0 |
| 10k | kube-state-metrics | pods | 2 | watch+initial | 0.18 | 102,949 |
| 10k | kube-state-metrics | deployments | 2 | watch+initial | 0.16 | 4,731 |
| 10k | kube-state-metrics | endpointslices | 2 | watch+initial | 0.12 | 2,063 |
| 10k | kube-state-metrics | jobs | 2 | watch+initial | 0.10 | 0 |
| 50k | collector | services | 1 | watch+initial | 0.37 | 3,620,969 |
| 50k | collector | pods | 1 | watch+initial | 0.09 | 111,531 |
| 50k | collector | namespaces | 1 | watch+initial | 0.02 | 0 |
| 50k | collector | resourcequotas | 1 | watch+initial | 0.02 | 0 |
| 50k | collector | nodes | 1 | watch+initial | 0.01 | 102,593 |
| 50k | collector | clusterresourcequotas | 1 | watch+initial | 0.01 | 0 |
| 50k | collector | cronjobs | 1 | watch+initial | 0.00 | 0 |
| 50k | collector | daemonsets | 1 | watch+initial | 0.00 | 0 |
| 50k | kube-state-metrics | configmaps | 2 | watch+initial | 1.19 | 45 |
| 50k | kube-state-metrics | deployments | 2 | watch+initial | 1.14 | 4,731 |
| 50k | kube-state-metrics | services | 2 | watch+initial | 1.12 | 3,620,969 |
| 50k | kube-state-metrics | replicasets | 2 | watch+initial | 1.07 | 0 |
| 50k | kube-state-metrics | secrets | 2 | watch+initial | 0.80 | 42 |
| 50k | kube-state-metrics | endpointslices | 2 | watch+initial | 0.46 | 2,063 |
| 50k | kube-state-metrics | jobs | 2 | watch+initial | 0.44 | 0 |
| 50k | kube-state-metrics | pods | 2 | watch+initial | 0.24 | 103,705 |
| 100k | collector | replicasets | 1 | watch+initial | 1.01 | 0 |
| 100k | collector | deployments | 1 | watch+initial | 0.99 | 4,731 |
| 100k | collector | services | 1 | watch+initial | 0.72 | 7,020,969 |
| 100k | collector | jobs | 1 | watch+initial | 0.34 | 0 |
| 100k | collector | cronjobs | 1 | watch+initial | 0.17 | 0 |
| 100k | collector | pods | 1 | watch+initial | 0.11 | 88,830 |
| 100k | collector | resourcequotas | 1 | watch+initial | 0.04 | 0 |
| 100k | collector | namespaces | 1 | watch+initial | 0.03 | 0 |
| 100k | kube-state-metrics | configmaps | 2 | watch+initial | 1.83 | 46,285 |
| 100k | kube-state-metrics | services | 2 | watch+initial | 1.69 | 7,020,969 |
| 100k | kube-state-metrics | replicasets | 2 | watch+initial | 1.68 | 0 |
| 100k | kube-state-metrics | deployments | 2 | watch+initial | 1.17 | 4,731 |
| 100k | kube-state-metrics | secrets | 2 | watch+initial | 1.12 | 5,653 |
| 100k | kube-state-metrics | endpointslices | 2 | watch+initial | 0.68 | 2,063 |
| 100k | kube-state-metrics | jobs | 2 | watch+initial | 0.68 | 0 |
| 100k | kube-state-metrics | cronjobs | 2 | watch+initial | 0.31 | 0 |
