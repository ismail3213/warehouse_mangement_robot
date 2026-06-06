import logging

logger = logging.getLogger("ScoringAgent")

def get_zone_id_from_pos(pos: str) -> int:
    """Helper to extract zone number from position string (e.g., 'Zone_2' -> 2)"""
    if not pos:
        return 1
    try:
        if "zone" in pos.lower():
            return int(pos.split("_")[1])
        elif "dock" in pos.lower():
            return int(pos.split("_")[1])
    except Exception:
        pass
    return 1

def score_dock(dock, target_zone_id: int, cargo_type: str) -> float:
    """
    Score a Dock. Score = Availability + Proximity to Storage + Compatibility
    - Availability: If FREE, +100. Else, 0 (disqualified).
    - Proximity: Distance between Dock and Target Storage Zone.
    - Compatibility: Certain docks might have special facilities (e.g., cold dock for cold cargo).
    """
    if dock.status != "FREE":
        return 0.0
        
    score = 100.0
    
    # Distance score: dock_id to target_zone_id
    # Dock 1 is close to Zone 1, etc.
    dist = abs(dock.dock_id - target_zone_id)
    distance_score = max(0.0, 50.0 - (dist * 10.0))  # Up to 50 points
    score += distance_score
    
    # Cargo compatibility
    # If cargo is Cold and dock_id is even, say it has cooling plugs
    if cargo_type.lower() == "cold":
        if dock.dock_id % 2 == 0:
            score += 20.0
            
    logger.info(f"Dock {dock.dock_id} scored: {score} (Dist Score: {distance_score})")
    return score

def score_storage_zone(zone, cargo_type: str, operation_type: str = "DELIVERY") -> float:
    """
    Score a Storage Zone. Score = Compatibility + Capacity Availability + Fill Level
    - Compatibility:
      - Cold cargo MUST go to Cold storage.
      - Hazardous cargo MUST go to Hazardous storage.
      - General/Electronics can go to corresponding or general storage.
    - Capacity:
      - For DELIVERY: Disqualify if zone occupied + 10 > capacity.
      - For PICKUP: Disqualify if zone occupied < 10.
    - Fill Level:
      - For DELIVERY: Prefer less saturated zones to distribute load.
      - For PICKUP: Prefer more saturated zones to free up space.
    """
    # Capacity checks
    if operation_type == "PICKUP":
        if zone.occupied < 10:
            return 0.0
    else:
        if zone.occupied + 10 > zone.capacity:
            return 0.0
        
    cargo_lower = cargo_type.lower() if cargo_type else "general"
    zone_type_lower = zone.product_type.lower() if zone.product_type else "general"
    
    # Compatibility strict rules
    if cargo_lower == "cold" and zone_type_lower != "cold":
        return 0.0
    if cargo_lower == "hazardous" and zone_type_lower != "hazardous":
        return 0.0
    if zone_type_lower == "cold" and cargo_lower != "cold":
        return 0.0
    if zone_type_lower == "hazardous" and cargo_lower != "hazardous":
        return 0.0
        
    score = 100.0  # Base compatibility score since it passed strict filters
    
    # Extra compatibility match
    if cargo_lower == zone_type_lower:
        score += 30.0
        
    # Saturation scoring
    if operation_type == "PICKUP":
        # Fuller is better (frees up critical storage capacity)
        full_ratio = zone.occupied / zone.capacity
        fill_score = full_ratio * 40.0
    else:
        # Emptier is better
        empty_ratio = 1.0 - (zone.occupied / zone.capacity)
        fill_score = empty_ratio * 40.0  # Up to 40 points
        
    score += fill_score
    
    logger.info(f"Zone {zone.zone_id} scored: {score} (Operation: {operation_type}, Fill Score: {fill_score:.1f})")
    return score

def score_robot(robot, source_dock_id: int) -> float:
    """
    Score a Robot. Score = Availability + Battery Level + Proximity
    - Availability: If status is AVAILABLE, +100. Else, 0 (disqualified).
    - Battery: If < 20%, 0 (disqualified, needs charge). Else, + battery * 0.5 (up to 50 pts).
    - Proximity: Distance from robot's current position to source dock.
    """
    if robot.status != "AVAILABLE":
        return 0.0
        
    if robot.battery < 20:
        return 0.0
        
    score = 100.0
    
    # Battery score
    battery_score = robot.battery * 0.5  # Up to 50 points
    score += battery_score
    
    # Distance from robot's current position to source dock
    robot_zone_id = get_zone_id_from_pos(robot.position)
    dist = abs(robot_zone_id - source_dock_id)
    distance_score = max(0.0, 50.0 - (dist * 12.0))  # Up to 50 points, penalizes distance
    score += distance_score
    
    logger.info(f"Robot {robot.robot_id} (at {robot.position}) scored: {score} (Battery Score: {battery_score}, Dist Score: {distance_score})")
    return score
