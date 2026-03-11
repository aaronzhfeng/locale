---
id: XN-020
title: "Phase 6 calibration: selective output improves precision from 89.4% to 92.9%"
date: 2026-03-11
dag_nodes: [I05, I07]
links:
  evidence_for: [I07]
  related_to: [XN-019, XN-018]
---

## Setup

Implemented calibration + selective output per proposal v2 Section 4.8:
- Edge features: endpoint disagreement, margins, degree, PE agreement, decision source
- Composite raw confidence score (weighted combination of features)
- Isotonic regression calibration (simplified Venn-Abers / PAV algorithm)
- Leave-one-network-out cross-validation (5 train, 1 test)
- Selective output: orient if calibrated confidence >= threshold, else "?"

## Results (FOR = 10% target)

| Network   | Total | Output | Abstain | Coverage | Precision | FOR   | Full Acc |
|-----------|-------|--------|---------|----------|-----------|-------|----------|
| Insurance | 43    | 43     | 0       | 100%     | 95.3%     | 4.7%  | 95.3%    |
| Alarm     | 43    | 40     | 3       | 93%      | 92.5%     | 7.5%  | 93.0%    |
| Sachs     | 17    | 14     | 3       | 82%      | 92.9%     | 7.1%  | 76.5%    |
| Child     | 25    | 22     | 3       | 88%      | 90.9%     | 9.1%  | 88.0%    |
| Asia      | 7     | 7      | 0       | 100%     | 100.0%    | 0.0%  | 100.0%   |
| Hepar2    | 64    | 57     | 7       | 89%      | 91.2%     | 8.8%  | 85.9%    |
| **Agg**   | 199   | 183    | 16      | **92%**  | **92.9%** | 7.1%  | 89.4%    |

## Key findings

1. **Selective output improves precision by +3.5pp** (89.4% → 92.9%) at 92% coverage
2. **Sachs benefits most**: 76.5% → 92.9% by abstaining on 3 hardest edges
3. **Hepar2**: 85.9% → 91.2% by abstaining on 7 edges
4. **Alarm slightly miscalibrated**: abstains 3 correct edges (93.0% → 92.5%)
5. FOR target not perfectly met: target 10%, achieved 7.1% (overcalibrated)

## Limitations

- Only 5 networks for leave-one-out calibration — very few training samples (~150 edges)
- Proposal mandates held-out GRAPH instances, not held-out networks. We don't have enough benchmark networks for proper cross-validation.
- Isotonic regression is a simplified Venn-Abers. True multiclass Venn-Abers would provide tighter coverage guarantees.
- Alarm miscalibration shows the feature set isn't universal across network structures.

## Conclusion

Selective output is a viable and valuable pipeline addition. The precision-coverage tradeoff is real and controllable. With more benchmark networks, calibration would improve. This validates the proposal's key insight that calibrated abstention is preferable to forced completion on uncertain edges.
