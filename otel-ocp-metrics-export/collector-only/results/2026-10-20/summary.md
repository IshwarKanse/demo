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
| scale-out: 1190 idle pods, statefulset with 2 replicas and target allocator | 1463 | 1190 | 19,370 | 0.25 / 0.27 | 2790 / 2946 | 1824 | 0 | 2,022 | 1,714 | 0.006 | 76 / 82 | 152 | 0 | 1.2 | 0.36 | 9312 | 53,214 | 0 / 0 |
| documented shape: 1190 idle pods, without kubelet proxy jobs | 1461 | 1190 | 2,437 | 0.05 / 0.05 | 629 / 665 | 735 | 0 | 1,129 | 1,714 | 0.006 | 84 / 88 | 153 | 0 | 0.2 | 0.34 | 9409 | 53,231 | 0 / 0 |
| rate: 1190 idle pods, 60s interval | 1461 | 1190 | 9,673 | 0.12 / 0.15 | 2157 / 2301 | 2347 | 0 | 1,714 | 847 | 0.003 | 84 / 86 | 146 | 0 | 0.6 | 0.33 | 9465 | 53,283 | 0 / 0 |
| rate: 1190 idle pods, 15s interval | 1461 | 1190 | 38,668 | 0.49 / 0.50 | 2273 / 2403 | 2400 | 0 | 520 | 3,421 | 0.011 | 64 / 70 | 152 | 0 | 2.3 | 0.40 | 9573 | 53,377 | 0 / 0 |
| long: 1190 idle pods, 150 min | 1461 | 1190 | 19,337 | 0.25 / 0.27 | 2537 / 2757 | 2558 | 0 | 789 | 1,710 | 0.005 | 68 / 76 | 153 | 0 | 1.2 | 0.36 | 9677 | 53,660 | 0 / 0 |
| documented shape: 0 idle pods, without kubelet proxy jobs | 271 | 0 | 2,050 | 0.05 / 0.05 | 570 / 600 | 673 | 0 | 1,020 | 480 | 0.002 | 54 / 60 | 138 | 0 | 0.2 | 0.33 | 9866 | 31,397 | 0 / 0 |
