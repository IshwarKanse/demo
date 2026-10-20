Cluster: OpenShift 5.0.0-0.nightly-2026-10-19-060022 on AWS, 7 nodes (4 workers, allocatable 15500m 60815304Ki each; control plane 3500m 14924844Ki each).
Collector image: registry.redhat.io/rhosdt/opentelemetry-collector-rhel9@sha256:af76e9b5eaa89400714f189c0bf94026e41bd3476920d4dd961ac217fff4630a.

Linear fit over the deployment tiers (cluster collector): working set 547 MiB + 1341 MiB per 1,000 pods, CPU 0.07 cores + 0.12 cores per 1,000 pods, 3,379 + 10,885 data points/s per 1,000 pods.

| run | pods running | idle pods | cluster collector: points/s | CPU avg / p95 | WSS MiB avg / max | RSS MiB max | refused/s max | queue max | node collector: points/s all nodes | busiest node CPU avg | busiest node WSS MiB avg / max | RSS MiB max | refused/s max | API server node proxy req/s | kube-apiserver CPU | kube-apiserver WSS MiB | option 1 remote write samples/s | restarts cluster / node |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tiers: 0 idle pods, deployment | 271 | 0 | 6,346 | 0.10 / 0.10 | 948 / 981 | 1052 | 0 | 993 | 481 | 0.002 | 49 / 56 | 139 | 0 | 1.2 | 0.34 | 8098 | 30,805 | 0 / 0 |
| tiers: 300 idle pods, deployment | 571 | 300 | 9,601 | 0.14 / 0.15 | 1246 / 1302 | 1325 | 0 | 700 | 790 | 0.003 | 57 / 63 | 140 | 0 | 1.2 | 0.35 | 8933 | 36,310 | 0 / 0 |
| tiers: 600 idle pods, deployment | 871 | 600 | 12,838 | 0.18 / 0.19 | 1717 / 1804 | 1755 | 0 | 0 | 1,100 | 0.004 | 59 / 63 | 144 | 0 | 1.2 | 0.35 | 9126 | 41,843 | 0 / 0 |
| tiers: 850 idle pods, deployment | 1121 | 850 | 15,538 | 0.21 / 0.22 | 2082 / 2226 | 2086 | 0 | 123,536 | 1,362 | 0.005 | 64 / 71 | 147 | 0 | 1.2 | 0.34 | 9318 | 46,534 | 0 / 0 |
| tiers: 1200 idle pods, deployment | 1471 | 1200 | 19,428 | 0.24 / 0.28 | 2510 / 2628 | 2458 | 0 | 78,938 | 1,720 | 0.005 | 72 / 76 | 153 | 0 | 1.2 | 0.35 | 9474 | 53,166 | 0 / 0 |
