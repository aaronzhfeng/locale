#!/bin/bash
# Re-run all 6 networks with N_SAMPLES=10000 for MosaCD-competitive skeleton coverage
set -e
cd /teamspace/studios/this_studio/auto_on/research-copilot

NETWORKS=("insurance" "alarm" "sachs" "child" "asia" "hepar2")

for net in "${NETWORKS[@]}"; do
    echo "=========================================="
    echo "Running $net with N_SAMPLES=10000"
    echo "$(date)"
    echo "=========================================="

    python projects/locale/experiments/mve_insurance.py \
        --network "$net" \
        --output-dir "projects/locale/experiments/results/mve_27b_${net}_10k" \
        --all-nodes \
        --disguise \
        --no-think \
        --n-samples 10000 \
        2>&1 | tee "projects/locale/experiments/results/mve_27b_${net}_10k.log"

    echo "Done: $net at $(date)"
    echo ""
done

echo "All networks complete at $(date)."
