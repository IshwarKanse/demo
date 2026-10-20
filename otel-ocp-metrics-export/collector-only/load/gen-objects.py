#!/usr/bin/env python3
"""Generate a large Kubernetes object inventory for the k8s_cluster receiver against kube-state-metrics comparison.

usage: load/gen-objects.py [--ns otel-load-objects] [--deployments 2000] [--running 300] [--configmaps 2000]
                           [--services 500] [--jobs 200] [--cronjobs 200] [--hpas 300] [--quotas 100] [--crqs 20]
                           [--only deployments,...]   > objects.yaml
Every object carries the label app.kubernetes.io/part-of=otel-load-objects and a `load-kind` label, so that one
kind can be deleted and recreated for the churn phase (oc delete deploy -n <ns> -l load-kind=deployment).
Deployments beyond --running have 0 replicas (one ReplicaSet each, no pod); the first --running ones run a
sleeping pod with the requests of the idle pods. Jobs run `true` once and stay as completed objects; CronJobs
are suspended; HPAs target the first --hpas deployments; ResourceQuotas limit a count that nothing reaches.
"""
import argparse, sys
p = argparse.ArgumentParser()
p.add_argument("--ns", default="otel-load-objects")
for name, default in (("deployments", 2000), ("running", 300), ("configmaps", 2000), ("services", 500), ("jobs", 200),
                      ("cronjobs", 200), ("hpas", 300), ("quotas", 100), ("crqs", 20)):
    p.add_argument("--" + name, type=int, default=default)
p.add_argument("--only", default="")
a = p.parse_args()
only = set(a.only.split(",")) if a.only else None
LABELS = "app.kubernetes.io/part-of: otel-load-objects"
POD = """      containers:
      - name: pause
        image: registry.access.redhat.com/ubi9/ubi-minimal:latest
        command: ["sleep", "infinity"]
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        resources:
          requests:
            cpu: 1m
            memory: 8Mi
          limits:
            memory: 32Mi"""
SEC = """      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault"""
SEC_CRON = """          securityContext:
            runAsNonRoot: true
            seccompProfile:
              type: RuntimeDefault"""
out = []
def emit(doc): out.append(doc.strip("\n"))
def want(kind): return only is None or kind in only
if want("namespace"):
    emit(f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {a.ns}
  labels:
    {LABELS}
    otel-load: "true"
""")
if want("deployments"):
    for i in range(a.deployments):
        emit(f"""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: load-dep-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: deployment
spec:
  replicas: {1 if i < a.running else 0}
  selector:
    matchLabels:
      app: load-dep-{i:04d}
  template:
    metadata:
      labels:
        app: load-dep-{i:04d}
        {LABELS}
    spec:
{SEC}
{POD}
""")
if want("configmaps"):
    for i in range(a.configmaps):
        emit(f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: load-cm-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: configmap
data:
  key: value-{i}
""")
if want("services"):
    for i in range(a.services):
        emit(f"""
apiVersion: v1
kind: Service
metadata:
  name: load-svc-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: service
spec:
  selector:
    app: load-dep-{i:04d}
  ports:
  - name: http
    port: 8080
    targetPort: 8080
""")
if want("jobs"):
    for i in range(a.jobs):
        emit(f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: load-job-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: job
spec:
  backoffLimit: 0
  template:
    metadata:
      labels:
        {LABELS}
    spec:
      restartPolicy: Never
{SEC}
      containers:
      - name: run
        image: registry.access.redhat.com/ubi9/ubi-minimal:latest
        command: ["true"]
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop: ["ALL"]
        resources:
          requests:
            cpu: 1m
            memory: 8Mi
""")
if want("cronjobs"):
    for i in range(a.cronjobs):
        emit(f"""
apiVersion: batch/v1
kind: CronJob
metadata:
  name: load-cron-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: cronjob
spec:
  schedule: "0 0 1 1 *"
  suspend: true
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: Never
{SEC_CRON}
          containers:
          - name: run
            image: registry.access.redhat.com/ubi9/ubi-minimal:latest
            command: ["true"]
            securityContext:
              allowPrivilegeEscalation: false
              capabilities:
                drop: ["ALL"]
""")
if want("hpas"):
    for i in range(a.hpas):
        emit(f"""
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: load-hpa-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: load-dep-{i:04d}
  minReplicas: 1
  maxReplicas: 2
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 90
""")
if want("quotas"):
    for i in range(a.quotas):
        emit(f"""
apiVersion: v1
kind: ResourceQuota
metadata:
  name: load-quota-{i:04d}
  namespace: {a.ns}
  labels:
    {LABELS}
    load-kind: quota
spec:
  hard:
    count/secrets: "100000"
""")
if want("crqs"):
    for i in range(a.crqs):
        emit(f"""
apiVersion: quota.openshift.io/v1
kind: ClusterResourceQuota
metadata:
  name: otel-load-crq-{i:04d}
  labels:
    {LABELS}
    load-kind: crq
spec:
  selector:
    labels:
      matchLabels:
        otel-load: "true"
  quota:
    hard:
      count/configmaps: "100000"
""")
sys.stdout.write("\n---\n".join(out) + "\n")
