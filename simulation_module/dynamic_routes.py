"""
Dynamic vehicle route injection based on Vision API data.
Bridges the Vision module (camera counts) to the SUMO simulation.
"""
import requests
import random


VISION_API_URL = "http://localhost:8000/get_traffic_count"

# Map lane directions to SUMO edge IDs (first available edges in each direction)
# These will be auto-populated from the network
LANE_EDGE_MAP = {}


def fetch_vision_data():
    """Fetch current vehicle counts from the Vision API."""
    try:
        resp = requests.get(VISION_API_URL, timeout=2)
        data = resp.json()
        return data.get("lanes", {}), data.get("total_vehicles", 0)
    except Exception:
        return {"north": 5, "south": 5, "east": 5, "west": 5}, 20  # fallback


def setup_edge_map(traci_module):
    """Auto-discover edges from the SUMO network for vehicle injection."""
    global LANE_EDGE_MAP
    edges = traci_module.edge.getIDList()
    # Filter out internal edges (start with ':')
    valid_edges = [e for e in edges if not e.startswith(':')]

    if len(valid_edges) >= 4:
        LANE_EDGE_MAP = {
            "north": valid_edges[0],
            "south": valid_edges[len(valid_edges) // 4],
            "east": valid_edges[len(valid_edges) // 2],
            "west": valid_edges[3 * len(valid_edges) // 4],
        }
    elif valid_edges:
        for i, direction in enumerate(["north", "south", "east", "west"]):
            LANE_EDGE_MAP[direction] = valid_edges[i % len(valid_edges)]


def inject_vehicles(traci_module, step, lane_counts):
    """Spawn vehicles in SUMO proportional to detected counts per lane."""
    if not LANE_EDGE_MAP:
        setup_edge_map(traci_module)

    for direction, count in lane_counts.items():
        edge = LANE_EDGE_MAP.get(direction)
        if not edge:
            continue

        # Spawn proportional vehicles (1 per 3 detected, cap at 5 per cycle)
        to_spawn = min(max(count // 3, 1), 5)

        for i in range(to_spawn):
            veh_id = f"vision_{direction}_{step}_{i}"
            try:
                # Pick a random destination edge
                all_edges = [e for e in traci_module.edge.getIDList() if not e.startswith(':')]
                dest = random.choice(all_edges)
                if dest != edge:
                    traci_module.vehicle.add(
                        vehID=veh_id,
                        routeID="",
                        typeID="DEFAULT_VEHTYPE",
                        depart="now",
                        departLane="best",
                        departSpeed="max",
                    )
                    traci_module.vehicle.changeTarget(veh_id, dest)
            except Exception:
                pass  # Edge may not be reachable, skip silently
