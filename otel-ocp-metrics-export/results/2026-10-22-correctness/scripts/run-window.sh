#!/bin/bash
# Timed run of the correctness check. Window 1 (steady, 12 min) starts at START; the stale target
# is scaled to 0 at START+5m. Window 2 (outage) is [START+12m, START+21m]: the OTLP sink is scaled
# to 0 at START+13m and back to 1 at START+15m, the rest is the replay. Every action and its time
# is appended to <outdir>/timeline.txt; collect.sh runs at the end.
# usage: scripts/run-window.sh <outdir> [START epoch seconds, default now+60]
set -uo pipefail
cd "$(dirname "$0")/.."
out=$(cd "$(dirname "$1")" 2>/dev/null && pwd)/$(basename "$1") || out=$1; start=${2:-$(( $(date +%s) + 60 ))}; ns=otel-correctness
mkdir -p "$out"; tl="$out/timeline.txt"
log() { echo "$(date -u +%FT%TZ) $(date +%s) $*" | tee -a "$tl"; }
waituntil() { local t=$1; local now; now=$(date +%s); [ "$now" -lt "$t" ] && sleep $((t - now)); }
w1s=$start; w1e=$((start + 12*60)); w2s=$w1e; w2e=$((start + 21*60))
log "plan window1=[$w1s,$w1e] stale-app-down=$((start+5*60)) sink-down=$((start+13*60)) sink-up=$((start+15*60)) window2=[$w2s,$w2e]"
waituntil "$w1s"; log "window1 start"
waituntil $((start + 5*60)); oc scale deploy/stale-app -n $ns --replicas=0 >/dev/null; log "stale-app scaled to 0"
waituntil "$w1e"; log "window1 end"
waituntil $((start + 13*60)); oc scale deploy/sink-prometheus -n $ns --replicas=0 >/dev/null
until [ "$(oc get pods -n $ns -l app=sink-prometheus --no-headers 2>/dev/null | wc -l | tr -d ' ')" = "0" ]; do sleep 2; done
log "sink scaled to 0 (pod gone)"
waituntil $((start + 15*60)); oc scale deploy/sink-prometheus -n $ns --replicas=1 >/dev/null; log "sink scaled to 1"
oc rollout status deploy/sink-prometheus -n $ns --timeout=3m >/dev/null; log "sink pod ready"
waituntil "$w2e"; log "window2 end"
sleep 90   # let the senders flush the tail of window 2
scripts/collect.sh "$out" "$w1s" "$w1e" "$w2s" "$w2e" 2>&1 | tee -a "$out/collect.log"
log "collect done"
