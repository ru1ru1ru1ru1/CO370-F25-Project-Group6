import pandas as pd
from pathlib import Path
import json

# Path to your unzipped GO GTFS data folder
GTFS_DIR = Path(r"./GO-GTFS")

# Path to the current JSON file per run, create the input JSON file based on the number you're assigned to.
ITINERARIES_FILE = Path(r"./input3.json") #<-- change this based on the number you are doing

OUTPUT_DIR = Path(r"./output3") #<-- change this based on the number you are doing

# If you're done, put your input.json and output to the folder

OUTPUT_DIR.mkdir(exist_ok=True)

LOG_FILE = OUTPUT_DIR / "log.txt"

# Target date is 2025-11-21
TARGET_SERVICE_ID = "20251121"

DEFAULT_MAX_ADVANCE_MIN = 5
DEFAULT_MAX_DELAY_MIN = 10
DEFAULT_MIN_WAIT_MIN = 2
DEFAULT_MAX_WAIT_MIN = 30
DEFAULT_CONNECTION_WEIGHT = 1.0

# Log, please check the log and then manually search for the correct stop id
_log_messages = []


def log(msg: str):
    _log_messages.append(msg)


def flush_log():
    if _log_messages:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            for line in _log_messages:
                f.write(line + "\n")

# Read data
stops = pd.read_csv(GTFS_DIR / "stops.txt")
routes = pd.read_csv(GTFS_DIR / "routes.txt")
trips = pd.read_csv(GTFS_DIR / "trips.txt")
stop_times = pd.read_csv(GTFS_DIR / "stop_times.txt")

# Convert GTFS HH:MM:SS (hours may be >= 24) to minutes from 00:00.
def gtfs_time_to_minutes(t_str: str):
    if pd.isna(t_str):
        return None
    h, m, s = map(int, t_str.split(":"))
    return h * 60 + m + s / 60.0

stop_times["arr_min"] = stop_times["arrival_time"].apply(gtfs_time_to_minutes)
stop_times["dep_min"] = stop_times["departure_time"].apply(gtfs_time_to_minutes)

# Filter trips & stop_times to TARGET_SERVICE_ID
trips_w = trips[trips["service_id"].astype(str) == str(TARGET_SERVICE_ID)].copy()

if trips_w.empty:
    log(f"[FATAL] No trips found with service_id={TARGET_SERVICE_ID}. "
        f"Check TARGET_SERVICE_ID and trips.txt.")
    flush_log()
    raise RuntimeError("No trips for TARGET_SERVICE_ID; see log.txt")

stop_times_w = stop_times[stop_times["trip_id"].isin(trips_w["trip_id"])].copy()

# Attach route_short_name/route_long_name to trips for filtering
trips_w = trips_w.merge(
    routes[["route_id", "route_short_name", "route_long_name"]],
    on="route_id",
    how="left"
)

# Read itineraries from JSON input
with open(ITINERARIES_FILE, "r", encoding="utf-8") as f:
    itineraries = json.load(f)

if not itineraries:
    log("[FATAL] itineraries.json is empty or missing itineraries.")
    flush_log()
    raise RuntimeError("No itineraries; see log.txt")

def find_trip_for_leg(
    route_short_name: str,
    origin_stop_id: str,
    dest_stop_id: str,
    dep_time_str: str,
    dep_window_min: int = 10,
):
    """
    Find a trip on a given route that:
      - Departs origin_stop_id around dep_time_str (+/- dep_window_min)
      - Later visits dest_stop_id (in stop_sequence order)

    Returns (trip_row, origin_row, dest_row) or (None, None, None).
    """
    target_dep_min = gtfs_time_to_minutes(dep_time_str)

    # Trips on this route
    trips_route = trips_w[trips_w["route_short_name"].astype(str) == str(route_short_name)]

    if trips_route.empty:
        log(f"[WARN] No trips found for route_short_name={route_short_name}")
        return None, None, None

    # stop_times at origin for those trips
    st_origin = stop_times_w[
        stop_times_w["trip_id"].isin(trips_route["trip_id"])
        & (stop_times_w["stop_id"].astype(str) == str(origin_stop_id))
    ].copy()

    if st_origin.empty:
        log(
            f"[WARN] No stop_times at origin_stop_id={origin_stop_id} "
            f"for route_short_name={route_short_name}"
        )
        return None, None, None

    # Filter by departure time
    st_origin = st_origin[
        (st_origin["dep_min"] >= target_dep_min - dep_window_min)
        & (st_origin["dep_min"] <= target_dep_min + dep_window_min)
    ]

    if st_origin.empty:
        log(
            f"[WARN] No origin departure within window for route={route_short_name}, "
            f"origin_stop_id={origin_stop_id}, dep_time={dep_time_str}"
        )
        return None, None, None

    # Try trips in order of closeness in time
    st_origin["time_diff"] = (st_origin["dep_min"] - target_dep_min).abs()
    st_origin = st_origin.sort_values("time_diff")

    for _, origin_row in st_origin.iterrows():
        trip_id = origin_row["trip_id"]
        st_trip = stop_times_w[stop_times_w["trip_id"] == trip_id].sort_values("stop_sequence")
        origin_seq = origin_row["stop_sequence"]

        # Look for destination stop
        cand_dest = st_trip[
            (st_trip["stop_id"].astype(str) == str(dest_stop_id))
            & (st_trip["stop_sequence"] >= origin_seq)
        ]
        if not cand_dest.empty:
            dest_row = cand_dest.iloc[0]
            trip_row = trips_route[trips_route["trip_id"] == trip_id].iloc[0]
            return trip_row, origin_row, dest_row

    log(
        f"[WARN] No trip found that goes origin_stop_id={origin_stop_id} "
        f"-> dest_stop_id={dest_stop_id} on route={route_short_name} "
        f"around dep_time={dep_time_str}"
    )
    return None, None, None


# Match GTFS trips 
selected_legs = []

for itin in itineraries:
    itin_name = itin.get("name", "unnamed")
    legs = itin.get("legs", [])
    if not legs:
        log(f"[WARN] Itinerary '{itin_name}' has no legs defined.")
        continue

    for leg_index, leg in enumerate(legs):
        trip_row, origin_row, dest_row = find_trip_for_leg(
            route_short_name=leg["route_short_name"],
            origin_stop_id=leg["origin_stop_id"],
            dest_stop_id=leg["dest_stop_id"],
            dep_time_str=leg["dep_time_str"],
            dep_window_min=10,
        )
        if trip_row is None:
            log(
                f"[ERROR] Itinerary '{itin_name}', leg '{leg.get('label')}' "
                f"could not be matched."
            )
            continue

        leg_info = {
            "itinerary": itin_name,
            "leg_index": leg_index,  # preserve order from JSON
            "leg_label": leg.get("label", f"leg_{leg_index}"),
            "trip_id": trip_row["trip_id"],
            "route_id": trip_row["route_id"],
            "route_short_name": trip_row["route_short_name"],
            "origin_stop_id": leg["origin_stop_id"],
            "dest_stop_id": leg["dest_stop_id"],
            "origin_dep_time": origin_row["departure_time"],
            "origin_dep_min": origin_row["dep_min"],
            "dest_arr_time": dest_row["arrival_time"],
            "dest_arr_min": dest_row["arr_min"],
        }
        selected_legs.append(leg_info)

selected_legs_df = pd.DataFrame(selected_legs)

if selected_legs_df.empty:
    log("[FATAL] No legs were matched. Check itineraries.json and GTFS data.")
    flush_log()
    raise RuntimeError("No legs matched; see log.txt")

# Find unique trips across all legs
unique_trips = (
    selected_legs_df[["trip_id", "route_id", "route_short_name"]]
    .drop_duplicates()
    .reset_index(drop=True)
)

unique_trips["max_advance_min"] = DEFAULT_MAX_ADVANCE_MIN
unique_trips["max_delay_min"] = DEFAULT_MAX_DELAY_MIN

trips_path = OUTPUT_DIR / "trips.csv"
unique_trips.to_csv(trips_path, index=False)
log(f"[INFO] Wrote {len(unique_trips)} trips to {trips_path}")

# Find connections between successive legs in each itinerary
#    hub_id = transfer stop_id (this might be hard to find, for example, UW has two different ID
#    may need manual effort to search and test by this script

connections = []
conn_id_counter = 1

for itin_name, sub in selected_legs_df.groupby("itinerary"):
    # Must be in the original order
    sub = sub.sort_values("leg_index").reset_index(drop=True)

    for i in range(len(sub) - 1):
        from_leg = sub.iloc[i]
        to_leg = sub.iloc[i + 1]

        hub_stop_id = from_leg["dest_stop_id"]

        if hub_stop_id != to_leg["origin_stop_id"]:
            log(
                f"[WARN] Transfer stop mismatch in itinerary '{itin_name}' "
                f"between legs '{from_leg['leg_label']}' and '{to_leg['leg_label']}'. "
                f"Using hub_stop_id={hub_stop_id}"
            )

        # Arrival Time of arrival-trip i at hub h
        arr_time_min = from_leg["dest_arr_min"]

        # Departure time of departure-trip j at hub h
        st_to = stop_times_w[
            (stop_times_w["trip_id"] == to_leg["trip_id"])
            & (stop_times_w["stop_id"].astype(str) == str(hub_stop_id))
        ]

        if st_to.empty:
            log(
                f"[ERROR] Could not find departure at hub={hub_stop_id} "
                f"for trip={to_leg['trip_id']} in itinerary '{itin_name}'"
            )
            continue

        dep_row = st_to.sort_values("stop_sequence").iloc[0]
        dep_time_min = dep_row["dep_min"]

        connections.append({
            "conn_id": f"C{conn_id_counter}",
            "arr_trip_id": from_leg["trip_id"],
            "dep_trip_id": to_leg["trip_id"],
            "hub_id": str(hub_stop_id),
            "arr_time_min": arr_time_min,
            "dep_time_min": dep_time_min,
            "min_wait_min": DEFAULT_MIN_WAIT_MIN,
            "max_wait_min": DEFAULT_MAX_WAIT_MIN,
            "weight": DEFAULT_CONNECTION_WEIGHT,
        })
        conn_id_counter += 1

connections_df = pd.DataFrame(connections)

if connections_df.empty:
    log("[WARN] No connections built (maybe all itineraries are single-leg).")

conns_path = OUTPUT_DIR / "connections.csv"
connections_df.to_csv(conns_path, index=False)
log(f"[INFO] Wrote {len(connections_df)} connections to {conns_path}")

flush_log()
