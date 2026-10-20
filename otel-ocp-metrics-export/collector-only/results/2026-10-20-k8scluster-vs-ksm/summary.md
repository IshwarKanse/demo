Cluster: OpenShift 5.0.0-0.nightly-2026-10-19-060022 on AWS, 7 nodes. Collector image: registry.redhat.io/rhosdt/opentelemetry-collector-rhel9@sha256:af76e9b5eaa89400714f189c0bf94026e41bd3476920d4dd961ac217fff4630a.

Inventory applied in 1248 s; full inventory seen by the collector before the apply ended (full deployment count reached 738 s before the apply ended (the collector lists objects as they are created; measured from create-inventory-applied/collector_inventory.csv)) and by kube-state-metrics 3 s after the apply ended (30 s scrape and collection intervals, 10 s polling); after a collector restart the full inventory was back after 35 s.

| phase | pods | deployments / replicasets / configmaps / services stored | collector CPU avg / p95 | collector WSS MiB avg / max | collector RSS MiB max | collector points/s | kube-state-metrics CPU avg / p95 | kube-state-metrics WSS MiB avg / max | kube-state-metrics RSS MiB max | kube-state-metrics samples per scrape | API server LIST/s | WATCH starts/s | open watches | kube-apiserver CPU | kube-controller-manager CPU | audit: collector list / watch | audit: kube-state-metrics list / watch |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 572 | 88 / 137 / 563 / 133 | 0.001 / 0.001 | 59 / 62 | 156 | 114 | 0.002 / 0.002 | 159 / 162 | 197 | 22,931 | 0.22 | 2.57 | 1808 | 0.72 | 0.02 | 0 / 0 | 0 / 0 |
| create | 573 | 2,088 / 2,148 / 2,587 / 633 | 0.004 / 0.007 | 123 / 156 | 217 | 494 | 0.004 / 0.010 | 166 / 184 | 199 | 95,030 | 12.64 | 2.52 | 1695 | 0.89 | 0.05 | 0 / 0 | 0 / 0 |
| steady | 573 | 2,088 / 2,147 / 2,566 / 633 | 0.004 / 0.005 | 136 / 148 | 212 | 566 | 0.003 / 0.003 | 166 / 167 | 170 | 106,682 | 20.13 | 2.94 | 1814 | 0.82 | 0.05 | 0 / 16 | 0 / 38 |
| restart | 573 | 2,088 / 2,147 / 2,566 / 633 | 0.004 / 0.004 | 121 / 144 | 216 | 503 | 0.003 / 0.003 | 167 / 169 | 172 | 106,736 | 20.23 | 3.08 | 1813 | 0.85 | 0.05 | 0 / 0 | 0 / 43 |
| churn | 573 | 2,088 / 2,147 / 2,566 / 633 | 0.006 / 0.012 | 137 / 167 | 221 | 444 | 0.006 / 0.013 | 183 / 205 | 201 | 83,426 | 12.44 | 3.02 | 1812 | 1.00 | 0.08 | 0 / 113 | 0 / 292 |
| steady2 | 573 | 2,088 / 2,147 / 2,566 / 633 | 0.004 / 0.005 | 155 / 165 | 221 | 563 | 0.003 / 0.003 | 165 / 167 | 175 | 106,736 | 20.16 | 3.03 | 1817 | 0.85 | 0.06 | 0 / 14 | 0 / 14 |
