#!/bin/bash
# Batch runner for LOCALE non-thinking experiments.
# Thinking mode deferred — needs per-condition max_tokens handling.

set -e
SCRIPT="projects/locale/experiments/mve_insurance.py"
RESULTS="projects/locale/experiments/results"

echo "=== LOCALE Batch Experiments (non-thinking) ==="
echo "Started: $(date)"
echo ""

# 1. Enriched Alarm rerun (unblocks XN-006)
echo ">>> [1/8] Enriched Alarm (fix XN-006 blocker)..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network alarm --disguise --no-think --enriched \
    --output-dir $RESULTS/mve_27b_enriched_alarm \
    2>&1 | tee $RESULTS/mve_27b_enriched_alarm/log.txt
echo ">>> [1/8] Done: $(date)"
echo ""

# 2. Sachs non-thinking (new benchmark)
echo ">>> [2/8] Sachs non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network sachs --disguise --no-think \
    --output-dir $RESULTS/mve_27b_sachs_disguised \
    2>&1 | tee $RESULTS/mve_27b_sachs_disguised/log.txt
echo ">>> [2/8] Done: $(date)"
echo ""

# 3. Child non-thinking (new benchmark)
echo ">>> [3/8] Child non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network child --disguise --no-think \
    --output-dir $RESULTS/mve_27b_child_disguised \
    2>&1 | tee $RESULTS/mve_27b_child_disguised/log.txt
echo ">>> [3/8] Done: $(date)"
echo ""

# 4. Insurance ego-v2 non-thinking (prompt optimization)
echo ">>> [4/8] Insurance ego-v2 non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network insurance --disguise --no-think --ego-v2 \
    --output-dir $RESULTS/mve_27b_insurance_v2 \
    2>&1 | tee $RESULTS/mve_27b_insurance_v2/log.txt
echo ">>> [4/8] Done: $(date)"
echo ""

# 5. Alarm ego-v2 non-thinking (prompt optimization)
echo ">>> [5/8] Alarm ego-v2 non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network alarm --disguise --no-think --ego-v2 \
    --output-dir $RESULTS/mve_27b_alarm_v2 \
    2>&1 | tee $RESULTS/mve_27b_alarm_v2/log.txt
echo ">>> [5/8] Done: $(date)"
echo ""

# 6. Insurance temp ladder non-thinking
echo ">>> [6/8] Insurance temp-ladder non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network insurance --disguise --no-think --temp-ladder \
    --output-dir $RESULTS/mve_27b_insurance_templad \
    2>&1 | tee $RESULTS/mve_27b_insurance_templad/log.txt
echo ">>> [6/8] Done: $(date)"
echo ""

# 7. Insurance contrastive PE non-thinking
echo ">>> [7/8] Insurance contrastive non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network insurance --disguise --no-think --contrastive \
    --output-dir $RESULTS/mve_27b_insurance_contrastive \
    2>&1 | tee $RESULTS/mve_27b_insurance_contrastive/log.txt
echo ">>> [7/8] Done: $(date)"
echo ""

# 8. Alarm contrastive PE non-thinking
echo ">>> [8/8] Alarm contrastive non-thinking..."
PYTHONUNBUFFERED=1 python3 $SCRIPT \
    --network alarm --disguise --no-think --contrastive \
    --output-dir $RESULTS/mve_27b_alarm_contrastive \
    2>&1 | tee $RESULTS/mve_27b_alarm_contrastive/log.txt
echo ">>> [8/8] Done: $(date)"
echo ""

echo "=== All batch experiments complete ==="
echo "Finished: $(date)"

# Run comparison
echo ""
echo ">>> Running comparison analysis..."
python3 projects/locale/experiments/compare_all.py
