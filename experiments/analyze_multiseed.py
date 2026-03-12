"""
Combined multi-seed analysis: LOCALE vs MosaCD.

Reads all completed multi-seed results and produces:
1. Per-network mean ± std for both methods
2. Head-to-head comparison table
3. Win/tie/loss summary

Usage:
    python analyze_multiseed.py --seeds 0 1 2 42 --networks insurance alarm sachs child asia
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pgmpy.utils


RESULTS_DIR = Path(__file__).parent / "results"
NETWORKS = ["insurance", "alarm", "sachs", "child", "asia", "hepar2"]


def compute_locale_f1(network, seed):
    """Compute F1 from LOCALE Phase 3 results."""
    # For seed=42, check symlink first, then original dir
    # For other seeds, only check the exact _s{seed} dir
    if seed == 42:
        candidates = [f"mve_27b_{network}_10k_k10_debiased_s42",
                      f"mve_27b_{network}_10k_k10_debiased"]
    else:
        candidates = [f"mve_27b_{network}_10k_k10_debiased_s{seed}"]

    for dirname in candidates:
        p3_path = RESULTS_DIR / dirname / "phase3_results.json"
        if p3_path.exists():
            break
    else:
        return None

    with open(p3_path) as f:
        p3 = json.load(f)

    model = pgmpy.utils.get_example_model(network)
    gt_edges = set(model.edges())

    ev = p3["evaluation"]
    tp = ev["correct"]
    total = ev["total"]
    fp = total - tp
    fn = len(gt_edges) - tp
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-10)

    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision,
            "recall": recall, "f1": f1, "n_gt": len(gt_edges), "n_skel": total}


def compute_mosacd_f1(network, seed):
    """Extract F1 from MosaCD results."""
    if seed == 42:
        candidates = [f"mosacd_{network}_s42", f"mosacd_{network}"]
    else:
        candidates = [f"mosacd_{network}_s{seed}"]

    for dirname in candidates:
        path = RESULTS_DIR / dirname / "mosacd_results.json"
        if path.exists():
            break
    else:
        return None

    with open(path) as f:
        d = json.load(f)

    m = d.get("metrics", {})
    if not m:
        return None

    return {"tp": m["tp"], "fp": m["fp"], "fn": m["fn"],
            "precision": m["precision"], "recall": m["recall"], "f1": m["f1"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 42])
    parser.add_argument("--networks", nargs="+", default=["insurance", "alarm", "sachs", "child", "asia"])
    args = parser.parse_args()

    print("=" * 90)
    print("Multi-Seed LOCALE vs MosaCD Comparison")
    print(f"Seeds: {args.seeds}")
    print("=" * 90)

    # Collect all results
    locale_results = {}  # {network: {seed: metrics}}
    mosacd_results = {}

    for net in args.networks:
        locale_results[net] = {}
        mosacd_results[net] = {}
        for seed in args.seeds:
            lm = compute_locale_f1(net, seed)
            if lm:
                locale_results[net][seed] = lm
            mm = compute_mosacd_f1(net, seed)
            if mm:
                mosacd_results[net][seed] = mm

    # Per-seed detail
    print(f"\n{'─'*90}")
    print("Per-Seed Detail")
    print(f"{'─'*90}")
    for net in args.networks:
        print(f"\n  {net.upper()}:")
        for seed in args.seeds:
            lm = locale_results[net].get(seed)
            mm = mosacd_results[net].get(seed)
            l_str = f"F1={lm['f1']:.3f} P={lm['precision']:.3f} R={lm['recall']:.3f}" if lm else "—"
            m_str = f"F1={mm['f1']:.3f} P={mm['precision']:.3f} R={mm['recall']:.3f}" if mm else "—"
            delta = ""
            if lm and mm:
                d = lm['f1'] - mm['f1']
                delta = f"  Δ={d:+.3f}"
            print(f"    seed={seed:>2}: LOCALE [{l_str}]  MosaCD [{m_str}]{delta}")

    # Summary table
    print(f"\n{'='*90}")
    print("Summary: Mean ± Std")
    print(f"{'='*90}")
    print(f"{'Network':<12} {'LOCALE F1':>16} {'MosaCD F1':>16} {'Delta':>10} {'Result':>8}")
    print("-" * 70)

    wins, ties, losses = 0, 0, 0

    for net in args.networks:
        l_f1s = [m["f1"] for m in locale_results[net].values()]
        m_f1s = [m["f1"] for m in mosacd_results[net].values()]

        if not l_f1s:
            continue

        l_mean, l_std = np.mean(l_f1s), np.std(l_f1s)
        l_str = f"{l_mean:.3f}±{l_std:.3f}"

        if m_f1s:
            m_mean, m_std = np.mean(m_f1s), np.std(m_f1s)
            m_str = f"{m_mean:.3f}±{m_std:.3f}"
            delta = l_mean - m_mean
            delta_str = f"{delta:+.3f}"

            # Win/tie/loss: >2pp = win, <-2pp = loss, else tie
            if delta > 0.02:
                result = "WIN"
                wins += 1
            elif delta < -0.02:
                result = "LOSS"
                losses += 1
            else:
                result = "TIE"
                ties += 1
        else:
            m_str = "—"
            delta_str = "—"
            result = "—"

        n_locale = len(l_f1s)
        n_mosacd = len(m_f1s)
        print(f"{net:<12} {l_str:>16} ({n_locale}) {m_str:>16} ({n_mosacd}) {delta_str:>10} {result:>8}")

    print("-" * 70)
    print(f"\nScore: LOCALE {wins}W / {ties}T / {losses}L  (>2pp threshold)")

    # Save to JSON
    summary = {
        "seeds": args.seeds,
        "networks": args.networks,
        "locale": {net: {str(s): v for s, v in seeds.items()}
                   for net, seeds in locale_results.items()},
        "mosacd": {net: {str(s): v for s, v in seeds.items()}
                   for net, seeds in mosacd_results.items()},
        "score": {"wins": wins, "ties": ties, "losses": losses},
    }
    out_path = RESULTS_DIR / "multiseed_comparison.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
