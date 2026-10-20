Cluster: OpenShift 5.0.0-0.nightly-2026-10-19-060022 on AWS, 7 nodes (4 workers, allocatable 15500m 60815304Ki each).

| run | kind | collector replicas | samples/s | series per replica | collector CPU avg / p95 | working set MiB avg / max | RSS MiB max | platform Prometheus CPU avg | platform Prometheus WSS MiB avg | UWM Prometheus CPU avg | UWM Prometheus WSS MiB avg | pending max | failed/s max | retried/s max | restarts | pods | load pods |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline: no remote write, 0 load pods | baseline | 1 | 0 | 498,069 | 0.00 / 0.00 | 23 / 23 | 0 | 0.22 | 3711 | 0.00 | 0 | 0 | 0 | 0 | 0 | 254 | 0 |
| series: 0 load pods, 30 s interval, 1 replica | steady | 1 | 27,973 | 513,773 | 0.28 / 0.30 | 98 / 128 | 162 | 0.29 | 5122 | 0.02 | 122 | 3,699 | 0 | 0 | 0 | 254 | 0 |
| series: 4 load pods, 30 s interval, 1 replica | steady | 1 | 35,074 | 615,763 | 0.37 / 0.39 | 105 / 146 | 165 | 0.32 | 5209 | 0.05 | 1023 | 3,578 | 0 | 0 | 0 | 258 | 4 |
| series: 10 load pods, 30 s interval, 1 replica | steady | 1 | 45,262 | 767,872 | 0.48 / 0.50 | 120 / 157 | 165 | 0.32 | 5176 | 0.10 | 1934 | 4,970 | 0 | 0 | 0 | 264 | 10 |
| series: 20 load pods, 30 s interval, 1 replica | steady | 1 | 62,168 | 1,021,233 | 0.66 / 0.70 | 132 / 167 | 163 | 0.33 | 5235 | 0.18 | 3551 | 29,529 | 0 | 0 | 0 | 274 | 20 |
| series: 40 load pods, 30 s interval, 1 replica | steady | 1 | 96,033 | 1,528,046 | 1.06 / 1.09 | 151 / 190 | 173 | 0.34 | 5369 | 0.35 | 7133 | 30,718 | 0 | 0 | 0 | 294 | 40 |
| rate: 10 load pods, 60s interval, 1 replica | steady | 1 | 37,182 | 1,450,947 | 0.39 / 0.41 | 125 / 162 | 169 | 0.36 | 5490 | 0.08 | 6810 | 4,468 | 0 | 0 | 0 | 264 | 10 |
| rate: 10 load pods, 15s interval, 1 replica | steady | 1 | 62,226 | 1,449,005 | 0.68 / 0.70 | 143 / 181 | 172 | 0.38 | 5592 | 0.19 | 6630 | 14,682 | 0 | 0 | 0 | 263 | 10 |
| replicas: 20 load pods, 30 s interval, 2 replicas | steady | 2 | 62,477 | 1,701,330 | 0.70 / 0.72 | 231 / 254 | 192 | 0.37 | 5556 | 0.22 | 8689 | 6,146 | 0 | 0 | 0 | 274 | 20 |
