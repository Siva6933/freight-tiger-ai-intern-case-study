# Code Review and Validation

## Scope
Reviewed the shipment aggregation, cost metric, comparison baselines, anomaly classification, contextual-note matching, and CSV output.

## Findings

1. **Weekly aggregation:** Shipment dates are grouped into Monday-to-Sunday weeks. Route-week costs are calculated from total freight cost divided by total tonne-kilometres.
2. **Historical baseline:** The code uses the previous eight available weekly observations, excluding the current week. If fewer than eight observations exist, it averages the available prior observations without padding.
3. **Peer baseline:** The comparison uses other routes with the same route type in the same week, excluding the current route.
4. **Anomaly threshold:** Increases greater than 20% against either available baseline are flagged for review. This threshold is a documented implementation choice.
5. **Contextual notes:** Notes are matched conservatively by route, time window, and evidence of increased costs. A note is not treated as proof of causation.
6. **Output schema:** The generated CSV has the same eight columns, in the same order, as the provided sample format.
7. **Reproducibility:** Three consecutive runs processed 2,940 shipments and generated 728 route-week rows. All three output files had the same SHA-256 hash:
   `63A42AEF08CF291F139881E675643FCAF4E4614F5EC7F538787DBF5B66C65B98`

## Current Results

- Flagged for human review: 17
- Justified anomalies: 3
- Other route-week rows: 708

## Limitations

- The 20% threshold is not prescribed by the case study and should be validated against labeled examples.
- Historical and peer comparisons may be unavailable when prior observations or same-type peer routes do not exist.
- Context notes are manually matched using explicit rules; this is not an LLM-based retrieval system.
- Identical output across runs demonstrates determinism, not the accuracy of every classification.
- The current validation covers output structure and reproducibility. Additional labeled test cases are needed to measure false positives and false negatives.
