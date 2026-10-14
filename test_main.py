import pandas as pd

from main import (
    OUTPUT_COLUMNS,
    add_comparison_baselines,
    build_weekly_costs,
    percentage_change,
)


def test_weekly_cost_uses_aggregated_tonne_km():
    shipments = pd.DataFrame({
        "origin": ["A", "A"],
        "destination": ["B", "B"],
        "route_type": ["Short", "Short"],
        "quantity_tonnes": [10, 20],
        "distance_km": [100, 100],
        "freight_cost_inr": [10000, 30000],
        "shipment_date": pd.to_datetime(["2025-01-06", "2025-01-07"]),
    })

    weekly = build_weekly_costs(shipments)

    # (10,000 + 30,000) / ((10 * 100) + (20 * 100))
    assert len(weekly) == 1
    assert weekly.iloc[0]["week_of"] == pd.Timestamp("2025-01-06")
    assert abs(weekly.iloc[0]["cost_per_tonne_km"] - (40000 / 3000)) < 1e-9


def test_baselines_exclude_current_week_and_current_route():
    weekly = pd.DataFrame({
        "route": ["A-B", "A-B", "C-D", "A-B", "C-D"],
        "route_type": ["Short"] * 5,
        "week_of": pd.to_datetime([
            "2025-01-06", "2025-01-13", "2025-01-13",
            "2025-01-20", "2025-01-20",
        ]),
        "cost_per_tonne_km": [10.0, 12.0, 20.0, 15.0, 25.0],
    })

    result = add_comparison_baselines(weekly)

    # A-B on Jan 13: only its previous observation is 10.
    row = result[
        (result["route"] == "A-B")
        & (result["week_of"] == pd.Timestamp("2025-01-13"))
    ].iloc[0]
    assert row["own_baseline"] == 10.0

    # A-B on Jan 13: the only other Short route that week is C-D at 20.
    assert row["peer_baseline"] == 20.0

    # A-B on Jan 20: own history averages 10 and 12, not current value 15.
    row = result[
        (result["route"] == "A-B")
        & (result["week_of"] == pd.Timestamp("2025-01-20"))
    ].iloc[0]
    assert row["own_baseline"] == 11.0

    # Peer baseline excludes A-B's 15 and uses C-D's 25.
    assert row["peer_baseline"] == 25.0


def test_percentage_change_and_output_schema():
    assert abs(percentage_change(12.0, 10.0) - 0.2) < 1e-9
    assert percentage_change(10.0, 0.0) is None
    assert OUTPUT_COLUMNS == [
        "route",
        "week_of",
        "cost_per_tonne_km",
        "vs_own_history",
        "vs_similar_routes",
        "flagged",
        "matched_note_id",
        "reason",
    ]


if __name__ == "__main__":
    tests = [
        test_weekly_cost_uses_aggregated_tonne_km,
        test_baselines_exclude_current_week_and_current_route,
        test_percentage_change_and_output_schema,
    ]

    for test in tests:
        test()
        print(f"PASS: {test.__name__}")

    print(f"\nAll {len(tests)} evaluation tests passed.")

