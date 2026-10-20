# k8s_cluster receiver scale limits (2026-10-20)

Follow-up to the [comparison at 5,000 objects](../2026-10-20-k8scluster-vs-ksm/README.md): the reviewer asked for the
limits of the `k8s_cluster` receiver against kube-state-metrics on a production-sized inventory (hundreds of thousands
of objects) instead of an extrapolation. The inventory was grown in steps on the same OpenShift 5.0 cluster (3 control
plane nodes m6i.xlarge with 4 vCPU and 16 GiB, 4 workers m5.4xlarge, 573 pods) and both clients were measured at every
step with the same phases. The ladder ended where the control plane ended, not where either client did.

## Method

- **Inventory** (`load/loader.py`, run as a Job in the cluster by `load/loader-driver.yaml`): one unit is one
  namespace with 1,000 created objects in the proportions of a busy cluster: 400 config maps, 263 secrets, 150
  deployments at 0 replicas (one ReplicaSet each, no pod), 100 headless services (one Endpoints and one
  EndpointSlice each), 50 suspended jobs, 30 suspended cron jobs, 6 resource quotas and the namespace. The first 10
  namespaces carry 30 HPAs each (300, a fixed control plane cost at every step) and 20 cluster resource quotas exist
  from the first step. Objects are created with plain POSTs from 24 parallel keep-alive connections inside the
  cluster (about 850 creates/s; 8 connections and 110 creates/s at the last step). The steps are additive: 10, 50,
  100 and 200 units (10k, 50k, 100k, 200k created objects; 21k, 78k, 147k and about 250k objects stored in etcd with
  the base cluster, the replica sets, endpoints and namespace defaults).
- **What each client watches**: the receiver has informers for pods, nodes, namespaces, replication controllers,
  resource quotas, services, daemon sets, deployments, replica sets, stateful sets, jobs, cron jobs, HPAs and
  cluster resource quotas; it has none for config maps, secrets or endpoints, which kube-state-metrics watches as
  well. The table therefore counts the objects *watched* by each client next to the objects stored, and the
  per-object figures are per watched object of that client. At 100k created objects the receiver watched 50k of the
  147k stored objects and kube-state-metrics 128k.
- **Phases per step** (`scripts/run-scale-ladder.sh`, same as the first comparison plus a kube-state-metrics restart):
  create (loader, then the time until both clients report every deployment, 3 min settle), steady (20 min),
  collector pod restart, kube-state-metrics pod restart (CMO recreates it), one churn cycle (the deployments of the
  first 10 % of the namespaces deleted with one deletecollection per namespace and recreated), steady2 (10 min). The
  audit log events of the two service accounts are pulled from the three control plane nodes right after each phase
  (`raw/audit/<step>-<phase>.jsonl`, summarised by `scripts/audit-scale.py`), and a control plane snapshot is taken
  before each create and after each phase (`raw/control-plane.jsonl`); the ladder stops when the snapshot before a
  create shows the control plane at its limit.
- **Instruments**: the collector under test is `08-k8scluster-collector.yaml` (the `k8s_cluster` receiver alone,
  30 s interval, product collector 0.158.0, 4Gi limit with the percentage memory_limiter, exported to the vendor
  stand-in Prometheus whose limit was raised to 24Gi for the series count); kube-state-metrics is the one of the
  monitoring stack (no limit, 1 min scrape), read through the platform Prometheus. Series exported by
  `scripts/export-series.sh` with `PROFILE=k8scluster-scale` (cAdvisor and the collectors' telemetry, the API server
  LIST and watch-list histograms, etcd size, kube-state-metrics scrape duration) into `raw/<run>/*.csv`, charts by
  `scripts/render-charts.py` (`charts/`), per-step table in `summary.md`.
- **Caveats**: the runner was restarted twice during the 10k step (a bash 3.2 quoting bug and a wrong
  kube-state-metrics check, both without effect on the measured windows; the 10k create and restart-ksm phases were
  finished from the saved timestamps); the "time to the inventory" values have the resolution of the clients'
  intervals (30 s collection, 60 s scrape, 5 s polling); the 100k create window contains the control plane stall
  described below and is not used for the fits.

## Results

Per step, steady averages over 20 min, maxima over all phases of the step (`summary.md` has every column):

| step (created) | stored / watched by collector / by kube-state-metrics | collector CPU steady, churn p95 | collector WSS steady, max, RSS max | collector points/s (points per cycle vs expected) | kube-state-metrics CPU steady, churn p95 | kube-state-metrics WSS steady, max, RSS max | kube-state-metrics samples per scrape, scrape s | inventory after create: collector / ksm | after restart: collector / ksm | kube-apiserver CPU (3), WSS max per instance | etcd db |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0k | 21k / 1.3k / 3.5k | 0.001 / - | 68 / 68 / 157 MiB | 119 (100 %) | 0.002 / - | 164 / 168 / 152 MiB | 23.6k, 0.1 | - | - | 0.87, 2.7 GiB | 70 MiB |
| 10k | 21k / 6.0k / 15k | 0.003 / 0.005 | 124 / 131 / 210 MiB | 470 (111 %) | 0.002 / 0.004 | 174 / 211 / 240 MiB | 86k, 0.2 | 5 s / 0 s | 35 s / 45 s | 0.82, 3.2 GiB | 109 MiB |
| 50k | 78k / 25k / 65k | 0.010 / 0.017 | 308 / 317 / 367 MiB | 1,719 (106 %) | 0.006 / 0.013 | 249 / 568 / 498 MiB | 321k, 0.8 | 0 s / 25 s | 35 s / 35 s | 0.82, 3.8 GiB | 267 MiB |
| 100k | 147k / 50k / 128k | 0.020 / 0.030 | 572 / 594 / 566 MiB | 3,278 (106 %) | 0.012 / 0.022 | 517 / 963 / 782 MiB | 614k, 1.7 | 10 s / 0 s | 36 s / 35 s | 1.18, 5.3 GiB | 419 MiB |
| 200k | stopped at about 186 units (250k stored): control plane limit, see below | | | | | | | | | 6.7 GiB during the create | 570 MiB |

Linear fits over the 0k to 100k steps, per watched object of each client:

- collector working set, steady: 56 MiB + 1.0 GiB per 100,000 watched objects (RSS max over a step: 153 MiB + 0.83 GiB
  per 100,000); CPU 0.02 cores per 50,000 watched objects at the 30 s interval.
- kube-state-metrics working set, steady: 127 MiB + 0.28 GiB per 100,000 watched objects (RSS max: 153 MiB + 0.5 GiB
  per 100,000); its scrape payload grows linearly, 6.1 samples per watched object, 614k samples and 1.7 s per scrape
  at 100k, which is what the platform Prometheus pays (5 to 6 GiB on the busiest replica).

What the phases showed:

- **The receiver keeps its interval at every step.** Accepted points per 30 s cycle match the inventory (106 to 111 %
  of the expected count; the excess is the per-container pod metrics), no refused point, no memory_limiter
  refusal, no restart, no OOM. Memory is linear in the watched objects with no step at a restart or a churn: the
  informer transform keeps only name, namespace, UID, labels, owner references and the few spec and status fields
  the metrics need.
- **Start-up is a watch-list stream, not a LIST.** The collector (client-go with the WatchListClient feature)
  re-establishes 14 watches with `sendInitialEvents=true` after a restart; the API server streams the inventory from
  its watch cache (`apiserver_watch_list_duration_seconds`: 1.0 s for the replica sets at 100k, 3.5 s for all 14
  streams together). kube-state-metrics does the same with 59 streams (two per resource; 1.8 s for the config maps,
  19 s in total at 100k). Neither client issued a single LIST in any window. The inventory was back 35 s after the
  pod start at every step for both: the time is the first collection cycle (30 s) or the first scrape (60 s), not the
  streaming. During the steady windows both only re-establish expiring watches (the collector 22 to 38, kube-state-
  metrics 58 to 83 in 20 min); the churn adds nothing visible.
- **The control plane is the limit, not the clients.** kube-apiserver memory grows with the stored objects (its watch
  cache holds every object for every client): 2.6 GiB per instance at 21k, 3.8 at 78k, 5.0 at 147k and 6.7 GiB
  during the 200k create, about 2 GiB per 100,000 stored objects per instance. The 24-connection create burst of the
  100k step (800 creates/s) overloaded the etcd leader for 70 s ("leader is overloaded likely from slow disk", one
  leader change, 500 and 504 responses, LIST p99 9 s in that window) while the clients kept their inventories (both
  had the 100k inventory 10 s after the loader ended). The 200k step was run with 8 connections and still went down
  to 110 creates/s with 500 and 504 retries; at about 186 units (250k stored objects) the three control plane nodes
  were at 89 to 99 % memory and CPU, the kube-apiserver on one node had restarted four times (probe timeouts under
  CPU starvation), the replica set controller was 7,000 objects behind, and the API became unreachable, so the
  loader was stopped and the inventory deleted in batches. Every kube-apiserver restart makes every informer in the
  cluster (operators, controllers, kube-state-metrics, the collector) re-stream the whole inventory, which keeps the
  nodes saturated: on 16 GiB control plane nodes the practical ceiling is about 150,000 stored objects, and beyond
  that the question is the control plane's, not the receiver's. Both clients cost the API server the same memory
  (one shared watch cache) and the same CPU per restart (one stream per informer).

## Limit found and recommendation

- No limit of the `k8s_cluster` receiver was reached up to 147,000 stored objects (50,000 watched): 0.6 GiB working
  set, 0.02 cores, interval kept, inventory back 35 s after a restart. The receiver's cost is about **1 GiB of
  working set and 0.04 cores per 100,000 watched objects** at a 30 s interval, with the RSS peak of a restart about
  1.2 times the steady working set. It costs roughly 4 times the memory of kube-state-metrics per watched object
  (1.0 against 0.28 GiB per 100,000) but watches 40 % of a typical inventory, because it has no informer for config
  maps, secrets or endpoints, so on the same cluster the two end up alike (572 against 517 MiB at 100k created).
- Sizing: give the cluster collector a memory limit of **2Gi per 100,000 objects the receiver watches** (deployments,
  replica sets, pods, services, jobs, cron jobs, HPAs, quotas, namespaces, nodes), which covers the steady working
  set, the restart peak and the memory_limiter headroom; the documented 4Gi limit covers clusters up to about
  200,000 watched objects, which is beyond what 16 GiB control plane nodes hold. The receiver is a single informer
  set per collector (`k8s_leader_elector` keeps it on one replica; the target allocator shards scrape targets, not
  informers), so it is not sharded: on a cluster that large, either accept one replica with a larger limit or take
  the kube_* metrics from the monitoring stack through remote write v2 (option 1), which also adds nothing to the
  control plane because kube-state-metrics is already running.
- Prefer remote write v2 from CMO over the receiver when the kube_* names, the custom resource metrics
  (opentelemetry-collector-contrib#50196) or the full inventory (config maps, secrets, endpoints) are needed, or when
  the control plane is already near its ceiling: a second full-cache client shares the watch cache but adds one more
  stream of every object at every API server restart.
- For the control plane: the cluster, not the collector, needs the planning above 150,000 objects on this node size
  (larger control plane nodes, faster etcd disks); any client that creates objects in bursts should stay well below
  the 800 creates/s that tipped the etcd leader here.

## Files

- `summary.md`: per-step table with every measured column, the fits and the start-up requests per resource.
- `charts/scale_memory_vs_objects.png`, `scale_cpu_vs_objects.png`, `scale_inventory_time.png`,
  `scale_control_plane.png`, `scale_timeline.png`.
- `runs.json`: one entry per phase and step with the window, the cluster shape, the collector image and the markers.
- `raw/<run>/*.csv`: the series of each window; `raw/audit/*.jsonl`, `raw/audit-requests.csv`, `raw/audit-lists.csv`:
  the audit log events and counts; `raw/control-plane.jsonl`: the snapshots; `raw/loader/*.log`: the loader
  summaries (rate, latency percentiles, retries per phase); `raw/phases.env`: the saved timestamps; `raw/ladder.log`
  and `raw/relief.log`: the runner log and the batched deletion at the end.
