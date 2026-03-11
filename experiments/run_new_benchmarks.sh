#!/bin/bash
# Run LOCALE pipeline on new benchmark networks
# Requires: RunPod vLLM endpoint active, GPU runtime
#
# Usage: bash run_new_benchmarks.sh [network_name]
# Examples:
#   bash run_new_benchmarks.sh asia
#   bash run_new_benchmarks.sh hailfinder
#   bash run_new_benchmarks.sh hepar2
#   bash run_new_benchmarks.sh all

set -e

NETWORKS="${1:-all}"

run_network() {
    local net=$1
    echo "============================================"
    echo "Running Phase 1 on: $net"
    echo "============================================"

    # Phase 1: LLM queries (ego + PE, K=5, disguised names, all nodes d>=2)
    python mve_insurance.py \
        --network "$net" \
        --disguised \
        --all-nodes \
        --K 5 \
        --output-dir "results/mve_27b_${net}_full"

    echo ""
    echo "Phase 1 complete for $net. Running post-processing..."

    # Enrich results with CI facts (for Phase 2)
    python enrich_results.py "results/mve_27b_${net}_full"

    # Phase 2: Max-2SAT constraint compilation
    python -c "
from phase2_max2sat import run_phase2
import json
r = run_phase2('results/mve_27b_${net}_full/mve_results.json')
with open('results/mve_27b_${net}_full/phase2_results.json', 'w') as f:
    json.dump(r, f, indent=2)
print(f'Phase 2: {r[\"summary\"][\"phase2_accuracy\"]}% (delta {r[\"summary\"][\"delta_pp\"]:+.1f}pp)')
"

    # Phase 3: Dual-endpoint reconciliation
    python -c "
from phase3_reconcile import run_phase3
import json
r = run_phase3('results/mve_27b_${net}_full')
if r:
    with open('results/mve_27b_${net}_full/phase3_results.json', 'w') as f:
        json.dump(r, f, indent=2)
    print(f'Phase 3: {r[\"evaluation\"][\"accuracy\"]*100:.1f}%')
"

    # Phase 4: Global acyclicity + safety valve
    python -c "
from phase4_global import run_phase4
import json
r = run_phase4('results/mve_27b_${net}_full')
if r:
    with open('results/mve_27b_${net}_full/phase4_results.json', 'w') as f:
        json.dump(r, f, indent=2)
    ev = r['evaluation']
    print(f'Phase 4: {ev[\"best_accuracy\"]*100:.1f}% (method: {ev[\"best_method\"]})')
"

    echo ""
    echo "$net pipeline complete!"
    echo ""
}

cd "$(dirname "$0")"

if [ "$NETWORKS" = "all" ]; then
    for net in asia hailfinder hepar2; do
        run_network "$net"
    done
else
    run_network "$NETWORKS"
fi

echo ""
echo "All done. Running comparison:"
python run_pipeline.py
