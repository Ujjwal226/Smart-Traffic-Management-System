"""
Green Wave coordination — offsets traffic light phases along corridors
so vehicles hitting green at one intersection also hit green at the next.
"""


def detect_corridors(traci_module):
    """
    Find sequences of traffic lights that share controlled lanes
    (i.e., are on the same road corridor).
    Returns list of corridors, each a list of TL IDs.
    """
    tl_ids = traci_module.trafficlight.getIDList()
    tl_lanes = {}

    for tl_id in tl_ids:
        lanes = set(traci_module.trafficlight.getControlledLanes(tl_id))
        # Extract edge IDs from lane IDs (lane = edge_id + "_" + lane_index)
        edges = set()
        for lane in lanes:
            parts = lane.rsplit("_", 1)
            if len(parts) == 2:
                edges.add(parts[0])
        tl_lanes[tl_id] = edges

    # Group TLs that share edges (connected on same road)
    corridors = []
    used = set()

    for tl_id in tl_ids:
        if tl_id in used:
            continue

        corridor = [tl_id]
        used.add(tl_id)

        for other_tl in tl_ids:
            if other_tl in used:
                continue
            # Check if they share any edges
            if tl_lanes[tl_id] & tl_lanes[other_tl]:
                corridor.append(other_tl)
                used.add(other_tl)

        if len(corridor) > 1:
            corridors.append(corridor)

    return corridors


def apply_green_wave(traci_module, corridors, base_green_duration=30):
    """
    Offset green phases along a corridor so a vehicle moving at ~50km/h
    will hit green at successive intersections.

    Offset between intersections ≈ distance / speed.
    Simplified: we use a fixed 5-second offset per intersection spacing.
    """
    OFFSET_PER_TL = 5  # seconds offset between successive TLs

    for corridor in corridors:
        for i, tl_id in enumerate(corridor):
            try:
                # Get current phase count
                logic = traci_module.trafficlight.getAllProgramLogics(tl_id)
                if not logic:
                    continue

                current_program = logic[0]
                phases = current_program.phases

                # Only offset if we have at least a green phase
                green_phases = [j for j, p in enumerate(phases) if 'G' in p.state]
                if not green_phases:
                    continue

                # Calculate offset for this TL in the corridor
                offset = (i * OFFSET_PER_TL) % base_green_duration

                # Apply by shifting phase timing
                # We set the TL to a specific phase based on the offset
                if offset > 0:
                    # Set initial phase offset
                    traci_module.trafficlight.setPhase(tl_id, green_phases[0])
                    traci_module.trafficlight.setPhaseDuration(
                        tl_id, max(base_green_duration - offset, 10)
                    )
            except Exception:
                continue  # Skip TLs with incompatible programs


def get_corridor_info(traci_module):
    """Return corridor info for dashboard display."""
    corridors = detect_corridors(traci_module)
    info = []
    for i, corridor in enumerate(corridors):
        info.append({
            "corridor_id": i + 1,
            "traffic_lights": list(corridor),
            "length": len(corridor),
        })
    return info
