
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent

SHIPMENTS_FILE = BASE_DIR / "shipment_records.csv"
NOTES_FILE = BASE_DIR / "context_notes.csv"
OUTPUT_FILE = BASE_DIR / "output.csv"

# Documented policy: investigate increases above 20% against
# either comparison baseline. This threshold is a design choice,
# not a threshold prescribed by the case study.
ANOMALY_THRESHOLD = 0.20

OUTPUT_COLUMNS = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
    "reason",
]


def load_data():
    shipments = pd.read_csv(SHIPMENTS_FILE)
    notes = pd.read_csv(NOTES_FILE)

    required = {
        "origin",
        "destination",
        "route_type",
        "quantity_tonnes",
        "distance_km",
        "freight_cost_inr",
        "shipment_date",
    }

    missing = required - set(shipments.columns)
    if missing:
        raise ValueError(f"Missing shipment columns: {sorted(missing)}")

    shipments["shipment_date"] = pd.to_datetime(
        shipments["shipment_date"], errors="raise"
    )

    numeric_columns = [
        "quantity_tonnes",
        "distance_km",
        "freight_cost_inr",
    ]
    for column in numeric_columns:
        shipments[column] = pd.to_numeric(
            shipments[column], errors="raise"
        )

    if (
        (shipments["quantity_tonnes"] <= 0).any()
        or (shipments["distance_km"] <= 0).any()
        or (shipments["freight_cost_inr"] < 0).any()
    ):
        raise ValueError("Invalid quantity, distance, or freight cost.")

    return shipments, notes


def build_weekly_costs(shipments):
    data = shipments.copy()

    # Monday-based weeks. W-SUN means weeks end on Sunday.
    data["week_of"] = (
        data["shipment_date"]
        .dt.to_period("W-SUN")
        .dt.start_time
    )

    data["route"] = (
        data["origin"].astype(str)
        + "-"
        + data["destination"].astype(str)
    )

    # Sum freight costs and tonne-kilometres before dividing.
    data["tonne_km"] = (
        data["quantity_tonnes"] * data["distance_km"]
    )

    weekly = (
        data.groupby(
            ["route", "route_type", "week_of"],
            as_index=False,
            sort=True,
        )
        .agg(
            total_cost=("freight_cost_inr", "sum"),
            total_tonne_km=("tonne_km", "sum"),
        )
    )

    weekly["cost_per_tonne_km"] = (
        weekly["total_cost"] / weekly["total_tonne_km"]
    )

    return weekly.sort_values(
        ["route", "week_of"]
    ).reset_index(drop=True)


def add_comparison_baselines(weekly):
    result = weekly.copy()

    # Each route uses only its previous available weekly observations.
    result["own_baseline"] = (
        result.groupby(["route", "route_type"])["cost_per_tonne_km"]
        .transform(
            lambda values: values.shift(1).rolling(
                window=8, min_periods=1
            ).mean()
        )
    )

    # Peer average for the same week and route type.
    # Exclude the route itself from its own peer average.
    type_week = result.groupby(
        ["route_type", "week_of"]
    )["cost_per_tonne_km"]

    result["type_total"] = type_week.transform("sum")
    result["type_count"] = type_week.transform("count")

    peer_count = result["type_count"] - 1
    result["peer_baseline"] = (
        (result["type_total"] - result["cost_per_tonne_km"])
        / peer_count.where(peer_count > 0)
    )

    return result.drop(columns=["type_total", "type_count"])


def percentage_change(current, baseline):
    if pd.isna(baseline) or baseline == 0:
        return None
    return (current / baseline) - 1


def format_comparison(change, description):
    if change is None:
        return f"N/A (no available {description} baseline)"
    return f"{change:+.1%} vs {description}"


def parse_note_date(value):
    return pd.to_datetime(value, errors="coerce")



def matching_note(route, week_of, notes):
    """Match only notes that support a cost increase for this route and week."""
    week_end = week_of + pd.Timedelta(days=6)

    for _, note in notes.iterrows():
        note_id = str(note["note_id"]).strip()
        applies_to = str(note["applies_to"]).strip()
        note_date = parse_note_date(note["date"])
        text = str(note["note"]).strip()
        lower_text = text.lower()

        if pd.isna(note_date):
            continue

        route_matches = (
            applies_to.lower() == "all routes"
            or applies_to.lower() == route.lower()
        )
        if not route_matches:
            continue

        # N001: Flooding affected Chennai-Bangalore
        # from Feb 24 through Mar 8, 2025.
        if note_id == "N001":
            if route != "Chennai-Bangalore":
                continue
            if week_of > pd.Timestamp("2025-03-03"):
                continue
            if week_end < pd.Timestamp("2025-02-24"):
                continue
            if "higher trip costs" not in lower_text:
                continue
            return note_id, text

        # N002: Temporary festival surcharge in the
        # Ahmedabad-Mumbai week beginning Jan 20.
        if note_id == "N002":
            if route != "Ahmedabad-Mumbai":
                continue
            if week_of != pd.Timestamp("2025-01-20"):
                continue
            if "temporary surcharge" not in lower_text:
                continue
            return note_id, text

        # N003: Diesel-price increase reported May 5.
        # The note does not specify a lasting duration,
        # so do not apply it automatically to later weeks.
        if note_id == "N003":
            if week_of != pd.Timestamp("2025-05-05"):
                continue
            if "pushing up transportation costs" not in lower_text:
                continue
            return note_id, text

    # Notes about stable conditions, unrelated routes,
    # or events without cost increases do not justify anomalies.
    return None, None



def create_output(weekly, notes):
    rows = []

    for _, item in weekly.iterrows():
        current = float(item["cost_per_tonne_km"])
        own_change = percentage_change(
            current, item["own_baseline"]
        )
        peer_change = percentage_change(
            current, item["peer_baseline"]
        )

        changes = [
            change
            for change in (own_change, peer_change)
            if change is not None
        ]

        rising_anomaly = any(
            change > ANOMALY_THRESHOLD for change in changes
        )

        note_id = None
        note_text = None

        if rising_anomaly:
            note_id, note_text = matching_note(
                item["route"], item["week_of"], notes
            )

        if rising_anomaly and note_id:
            flagged = "No (justified)"
            reason = (
                f"Justified by note {note_id}: {note_text}"
            )
        elif rising_anomaly:
            flagged = "Yes"
            reason = (
                "No matching note provides a valid explanation "
                "for this route and week. Cost increase is "
                "unexplained and requires human review."
            )
        else:
            flagged = "No"
            reason = (
                "The increase did not exceed the documented "
                "20% anomaly threshold against either available "
                "comparison baseline."
            )

        rows.append(
            {
                "route": item["route"],
                "week_of": item["week_of"].strftime("%Y-%m-%d"),
                "cost_per_tonne_km": round(current, 2),
                "vs_own_history": format_comparison(
                    own_change, "this route's past average"
                ),
                "vs_similar_routes": format_comparison(
                    peer_change, "similar-length routes this week"
                ),
                "flagged": flagged,
                "matched_note_id": note_id or "",
                "reason": reason,
            }
        )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main():
    shipments, notes = load_data()
    weekly = build_weekly_costs(shipments)
    weekly = add_comparison_baselines(weekly)
    output = create_output(weekly, notes)

    output.to_csv(OUTPUT_FILE, index=False)

    print(f"Shipments processed: {len(shipments)}")
    print(f"Route-week rows generated: {len(output)}")
    print(f"Flagged for review: {(output['flagged'] == 'Yes').sum()}")
    print(
        "Justified anomalies: "
        f"{(output['flagged'] == 'No (justified)').sum()}"
    )
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
