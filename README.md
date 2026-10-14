# Freight Tiger — Shipment Cost Anomaly Analysis

## Overview
This project analyzes shipment records to identify unusual changes in transportation cost per tonne-kilometre across routes and weeks.

## Inputs
- `shipment_records.csv` — shipment-level input data.
- `context_notes.csv` — contextual notes used to assess potential explanations for cost increases.

## Method
1. Process shipment records and aggregate costs by route and week.
2. Compare weekly costs with the route's historical baseline and similar-length routes.
3. Flag increases exceeding the configured 20% threshold against either available baseline.
4. Match relevant contextual notes to explain supported anomalies.
5. Export the results to `output.csv` for review.

The 20% threshold is an implementation choice, not a threshold prescribed by the case study.

## Run locally
Python 3 and pandas are required.

```powershell
python -m pip install pandas
python main.py
```

## Output
`output.csv` contains route-week costs, baseline comparisons, review flags, matched note IDs, and explanations.

An automated flag is an indication for investigation, not proof of an error or misconduct.

## Validation and reproducibility

The analysis was run three consecutive times on the same input files.

- Shipments processed per run: 2,940
- Route-week rows generated per run: 728
- Review flags per run: 17
- Justified anomalies per run: 3
- Result: all three output CSV files were byte-for-byte identical.

SHA-256 for each output:
`63A42AEF08CF291F139881E675643FCAF4E4614F5EC7F538787DBF5B66C65B98`

This verifies repeatability on the tested inputs. It does not establish that every anomaly decision is correct.

## LLM usage and cost

The current implementation uses deterministic Python and pandas rules. It makes **0 LLM calls**, processes **0 LLM input tokens**, and generates **0 LLM output tokens**. LLM API cost for this run is therefore **$0**. Local compute and electricity costs were not measured.

## Review notes

See `REVIEW.md` for code-review findings, validation evidence, and limitations. See `DECISIONS.md` for implementation choices.

## Automated evaluation tests

Run the checks with:

```powershell
python test_main.py
```

The three synthetic-data tests verify:
- Weekly cost aggregation using total freight cost divided by total tonne-kilometres.
- Historical baselines excluding the current week.
- Peer baselines excluding the current route.
- Percentage-change behavior and output column names.

All three tests passed during local validation. These tests cover core calculation rules but are not a complete accuracy evaluation of every anomaly classification.
