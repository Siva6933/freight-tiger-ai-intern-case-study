# Design Decisions

## 1. Analysis granularity
Shipment records are aggregated by route and week to make changes easier to compare over time.

## 2. Cost metric
The analysis uses cost per tonne-kilometre to compare transportation costs across routes.

## 3. Anomaly threshold
An increase greater than 20% against either available comparison baseline is treated as a potential anomaly. This is a documented design choice, not a threshold prescribed by the case study.

## 4. Comparison baselines
Weekly costs are compared against the route's historical baseline and similar-length routes for the same week. Comparisons are omitted when a baseline is unavailable.

## 5. Contextual note matching
A note is used as a justification only when its route, timing, and content support the observed increase. Notes describing stable conditions, unrelated routes, or events that did not affect rates are not sufficient evidence.

The diesel-price note is matched only to its stated start week because the note does not establish how long its effect persisted.

## 6. Review outcomes
- `Yes`: an anomaly requires human review because no supporting note was matched.
- `No (justified)`: an anomaly has a matching contextual explanation.
- `No`: neither available baseline shows an increase exceeding the configured threshold.

## 7. Limitations
Historical comparisons depend on data availability and quality. A matched note is supporting context, not independent proof of causation. Unmatched anomalies require further investigation.
