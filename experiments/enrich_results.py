"""
Enrich existing Phase 1 results with CI facts and GT edges.
Avoids re-running LLM queries — just recomputes skeleton info.
"""

import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from mve_insurance import (
    load_network, sample_data, estimate_skeleton, get_ego_graph_info,
    NETWORK_CONFIGS, N_SAMPLES, SEED_DATA
)


def enrich(results_path):
    with open(results_path) as f:
        data = json.load(f)

    meta = data.get("metadata", {})
    network = meta.get("network", "insurance")
    net_cfg = NETWORK_CONFIGS[network]

    # Load network and skeleton
    model, gt_edges = load_network(net_cfg["pgmpy_name"])
    np.random.seed(SEED_DATA)
    sampled = sample_data(model)
    skeleton, sep_sets = estimate_skeleton(sampled)

    # Enrich per_node
    for node, info in data.get("per_node", {}).items():
        if "ci_facts" in info and "gt_edges" in info:
            continue  # already enriched

        neighbors, neighbor_adj, ci_facts, edges_to_orient = get_ego_graph_info(
            node, skeleton, sep_sets, gt_edges
        )
        info["neighbors"] = neighbors
        info["ci_facts"] = ci_facts
        info["gt_edges"] = [list(e) for e in edges_to_orient]

    with open(results_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Enriched {results_path}")


if __name__ == "__main__":
    results_dir = Path("projects/locale/experiments/results")
    targets = [
        "mve_27b_insurance_full",
        "mve_27b_alarm_full",
        "mve_27b_sachs_full",
        "mve_27b_child_full",
        "mve_27b_disguised",
        "mve_27b_alarm_disguised",
    ]
    for dirname in targets:
        path = results_dir / dirname / "mve_results.json"
        if path.exists():
            enrich(str(path))
