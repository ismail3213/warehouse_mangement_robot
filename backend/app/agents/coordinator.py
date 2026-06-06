import os
import datetime
import logging
import joblib
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from ..models import Truck, Dock, Robot, Zone, Mission, DecisionLog
from .scoring import score_dock, score_storage_zone, score_robot
from ..mqtt_client import mqtt_manager

logger = logging.getLogger("CoordinatorAgent")

# Path to the trained XGBoost model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "eta_model.pkl")

# Dock to Zone mapping (Dock 1 unloads into Zone 1, etc.)
DOCK_TO_ZONE = {1: 1, 2: 2, 3: 3, 4: 4}

def predict_eta_minutes(distance: float, traffic_level: int, weather: int, route_risk: int, driver_fatigue: int, route_id: str = None, db: Session = None) -> float:
    """
    Predict ETA in minutes using XGBoost model.
    Checks for active incidents on the selected route and adds delay.
    Fallback to heuristic if model is not available.
    """
    incident_delay = 0
    if route_id and db:
        try:
            from ..models import Incident
            active_incidents = db.query(Incident).filter(Incident.route_id == route_id, Incident.active == True).all()
            incident_delay = sum(inc.delay_minutes for inc in active_incidents)
            if incident_delay > 0:
                logger.info(f"Active incident delay detected on {route_id}: +{incident_delay} minutes")
        except Exception as e:
            logger.error(f"Error reading incidents: {e}")

    predicted_time = 0.0
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            # Features: distance, traffic_level, weather, route_risk, driver_fatigue
            features = np.array([[distance, traffic_level, weather, route_risk, driver_fatigue]])
            prediction = model.predict(features)
            predicted_time = float(prediction[0])
            logger.info(f"ETA predicted by XGBoost model: {predicted_time:.2f} minutes")
            predicted_time = max(10.0, predicted_time)
        except Exception as e:
            logger.error(f"Error predicting with XGBoost model: {e}. Falling back to heuristic.")
            
    if predicted_time == 0.0:
        # Heuristic fallback: Base speed 50 mph + traffic/weather/risk delays
        base_time = (distance / 50.0) * 60.0
        traffic_delay = traffic_level * 25.0
        weather_delay = weather * 15.0
        risk_delay = route_risk * 10.0
        fatigue_delay = driver_fatigue * 5.0
        predicted_time = base_time + traffic_delay + weather_delay + risk_delay + fatigue_delay
        logger.info(f"ETA predicted by heuristic: {predicted_time:.2f} minutes")
        predicted_time = max(10.0, predicted_time)
        
    return predicted_time + incident_delay

def log_decision(db: Session, decision_type: str, reason: str, source: str = "Coordinator"):
    """Insert a log entry into decision_logs table"""
    db_log = DecisionLog(
        decision_type=decision_type,
        decision_reason=reason,
        agent_source=source
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    # Also publish to MQTT
    mqtt_manager.publish("alert/new", {
        "event": "DECISION_LOG",
        "type": decision_type,
        "reason": reason,
        "source": source,
        "timestamp": str(datetime.datetime.now())
    })

def orchestrate_truck_arrival(
    db: Session,
    supplier: str,
    cargo_type: str,
    distance: float,
    traffic_level: int,
    weather: int,
    route_risk: int,
    driver_fatigue: int,
    priority: int,
    origin: str = "North Hub",
    operation_type: str = "DELIVERY",
    route_id: str = "Route_1"
) -> dict:
    """
    Core orchestrator:
    1. Predict ETA
    2. Select best Storage Zone
    3. Select best Dock
    4. Select best Robot
    5. Spawn Mission or Queue Truck
    """
    logger.info(f"New truck arrival requested: {supplier} carrying {cargo_type} for {operation_type} via {route_id}")
    
    # 1. Predict ETA
    eta_mins = predict_eta_minutes(distance, traffic_level, weather, route_risk, driver_fatigue, route_id, db)
    eta_time = datetime.datetime.now() + datetime.timedelta(minutes=eta_mins)
    
    # Create the Truck
    truck = Truck(
        supplier=supplier,
        cargo_type=cargo_type,
        eta=eta_time,
        priority=priority,
        status="PENDING",
        origin=origin,
        operation_type=operation_type,
        route_id=route_id,
        gps_progress=0.0
    )
    db.add(truck)
    db.commit()
    db.refresh(truck)
    
    # Publish truck pending
    mqtt_manager.publish("truck/arrival", {
        "truck_id": truck.truck_id,
        "supplier": truck.supplier,
        "cargo_type": truck.cargo_type,
        "eta": str(truck.eta),
        "priority": truck.priority,
        "status": truck.status,
        "origin": truck.origin,
        "operation_type": truck.operation_type,
        "route_id": truck.route_id,
        "gps_progress": truck.gps_progress
    })
    
    # JIT ALLOCATION LOGIC:
    # If this is a remote supplier delivery, do NOT allocate dock/robot yet. Let it travel first.
    if not truck.is_company_truck and operation_type == "DELIVERY" and distance > 0:
        reason = f"Supplier truck {truck.truck_id} ({supplier}) dispatched. En route via {route_id} with ETA {str(truck.eta)}. Resources will be allocated JIT upon arrival."
        log_decision(db, "TRUCK_DISPATCHED_JIT", reason)
        return {
            "status": "PENDING_EN_ROUTE",
            "truck_id": truck.truck_id,
            "eta": str(truck.eta),
            "reason": "En route. Docks will be assigned JIT upon arrival."
        }
        
    # 2. Find best Storage Zone
    zones = db.query(Zone).all()
    zone_scores = {}
    for zone in zones:
        score = score_storage_zone(zone, cargo_type, operation_type)
        if score > 0:
            zone_scores[zone.zone_id] = (zone, score)
            
    if not zone_scores:
        reason = f"Truck {truck.truck_id} rejected. No compatible storage zone available for cargo type '{cargo_type}'."
        truck.status = "REJECTED"
        db.commit()
        log_decision(db, "TRUCK_REJECTED", reason)
        return {"status": "REJECTED", "reason": reason, "truck_id": truck.truck_id}
        
    selected_zone, best_zone_score = max(zone_scores.values(), key=lambda x: x[1])
    logger.info(f"Selected Storage Zone {selected_zone.zone_id} for cargo {cargo_type} (score: {best_zone_score:.1f})")
    
    # 3. Find best Dock
    docks = db.query(Dock).all()
    dock_scores = {}
    for d in docks:
        score = score_dock(d, selected_zone.zone_id, cargo_type)
        if score > 0:
            dock_scores[d.dock_id] = (d, score)
            
    if not dock_scores:
        # Queue the truck: all docks are full
        truck.status = "QUEUED"
        db.commit()
        
        reason = f"No docks available. Truck {truck.truck_id} ({supplier}) added to QUEUE. Cargo type: {cargo_type}."
        log_decision(db, "TRUCK_QUEUED", reason)
        
        mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "QUEUED"})
        return {
            "status": "QUEUED",
            "truck_id": truck.truck_id,
            "eta": str(truck.eta),
            "reason": "All docks are currently occupied."
        }
        
    selected_dock, best_dock_score = max(dock_scores.values(), key=lambda x: x[1])
    logger.info(f"Selected Dock {selected_dock.dock_id} (score: {best_dock_score:.1f})")
    
    # 4. Find best Robot
    # Dock unloads to its corresponding zone
    source_zone_id = DOCK_TO_ZONE.get(selected_dock.dock_id, 1)
    
    robots = db.query(Robot).all()
    robot_scores = {}
    for r in robots:
        score = score_robot(r, selected_dock.dock_id)
        if score > 0:
            robot_scores[r.robot_id] = (r, score)
            
    if not robot_scores:
        # Assigned dock, but no robot available: mission is queued
        selected_dock.status = "OCCUPIED"
        selected_dock.current_truck = truck.truck_id
        truck.status = "PENDING"  # In-transit PENDING
        db.commit()
        
        reason = (f"Optimized routing complete. Truck {truck.truck_id} ({supplier}) dispatched via {route_id} to Dock {selected_dock.dock_id} (Score: {best_dock_score:.1f}). "
                  f"No available robots at this moment; mission will queue upon arrival.")
        log_decision(db, "DOCK_ASSIGNED_NO_ROBOT", reason)
        
        mqtt_manager.publish("dock/status", {"dock_id": selected_dock.dock_id, "status": "OCCUPIED", "current_truck": truck.truck_id})
        mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "PENDING"})
        return {
            "status": "DISPATCHED_WAITING_ROBOT",
            "truck_id": truck.truck_id,
            "dock_id": selected_dock.dock_id,
            "zone_id": selected_zone.zone_id,
            "reason": "Dock assigned, truck is traveling. No robots available currently."
        }
        
    selected_robot, best_robot_score = max(robot_scores.values(), key=lambda x: x[1])
    logger.info(f"Selected Robot {selected_robot.robot_id} (score: {best_robot_score:.1f})")
    
    # 5. All resources assigned! Spawn mission immediately.
    # Update Truck (in transit)
    truck.status = "PENDING"
    
    # Update Dock
    selected_dock.status = "OCCUPIED"
    selected_dock.current_truck = truck.truck_id
    
    # Update Robot (reserved)
    selected_robot.status = "BUSY"
    
    # Route logic for DELIVERY vs PICKUP
    dock_zone_id = DOCK_TO_ZONE.get(selected_dock.dock_id, 1)
    if operation_type == "PICKUP":
        mission_source = selected_zone.zone_id
        mission_destination = dock_zone_id
    else:
        mission_source = dock_zone_id
        mission_destination = selected_zone.zone_id

    # Create Mission (starts as PENDING during transit)
    mission = Mission(
        robot_id=selected_robot.robot_id,
        source_zone=mission_source,
        destination_zone=mission_destination,
        status="PENDING",
        operation_type=operation_type,
        truck_id=truck.truck_id if truck else None
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    
    # Adjust capacity in zone
    if operation_type == "PICKUP":
        selected_zone.occupied = max(0, selected_zone.occupied - 10)
    else:
        selected_zone.occupied = min(selected_zone.capacity, selected_zone.occupied + 10)
    db.commit()
    
    reason = (f"Optimized routing complete. Truck {truck.truck_id} ({supplier}) docked at Dock {selected_dock.dock_id} (Score: {best_dock_score:.1f}). "
              f"Cargo allocated to Zone {selected_zone.zone_id} ({selected_zone.product_type}, Score: {best_zone_score:.1f}). "
              f"Robot {selected_robot.robot_id} assigned (Score: {best_robot_score:.1f}). Mission {mission.mission_id} ({operation_type}) started.")
    log_decision(db, "ROUTING_SUCCESS", reason)
    
    # Publish MQTT statuses
    mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "PROCESSING"})
    mqtt_manager.publish("dock/status", {"dock_id": selected_dock.dock_id, "status": "OCCUPIED", "current_truck": truck.truck_id})
    mqtt_manager.publish("robot/status", {"robot_id": selected_robot.robot_id, "status": "BUSY", "position": f"Zone_{mission_source}"})
    mqtt_manager.publish("mission/create", {
        "mission_id": mission.mission_id,
        "robot_id": selected_robot.robot_id,
        "source_zone": mission_source,
        "destination_zone": mission_destination,
        "status": "RUNNING",
        "operation_type": operation_type
    })
    
    return {
        "status": "PROCESSING",
        "truck_id": truck.truck_id,
        "dock_id": selected_dock.dock_id,
        "zone_id": selected_zone.zone_id,
        "robot_id": selected_robot.robot_id,
        "mission_id": mission.mission_id,
        "eta": str(truck.eta)
    }

def handle_mission_completion(db: Session, mission_id: int):
    """
    Marks mission completed, releases robot, releases dock and truck.
    """
    mission = db.query(Mission).filter(Mission.mission_id == mission_id).first()
    if not mission or mission.status == "COMPLETED":
        return
        
    mission.status = "COMPLETED"
    mission.completed_at = datetime.datetime.now()
    
    # Release robot
    robot = db.query(Robot).filter(Robot.robot_id == mission.robot_id).first()
    if robot:
        robot.status = "AVAILABLE"
        # Simulate battery depletion
        robot.battery = max(10, robot.battery - 12)
        # Robot position is now the destination zone of the mission
        robot.position = f"Zone_{mission.destination_zone}"
        
    # Find dock and truck to release using robust operation-aware matching
    dock_id = None
    if mission.truck_id:
        dock = db.query(Dock).filter(Dock.current_truck == mission.truck_id).first()
        if dock:
            dock_id = dock.dock_id
            
    if dock_id:
        dock = db.query(Dock).filter(Dock.dock_id == dock_id).first()
        if dock and dock.current_truck:
            truck = db.query(Truck).filter(Truck.truck_id == dock.current_truck).first()
            if truck:
                if truck.is_company_truck:
                    # Company truck completed loading! Let it depart for client
                    truck.company_truck_status = "EN_ROUTE_TO_CLIENT"
                    truck.status = "EN_ROUTE"
                    truck.gps_progress = 0.0
                    truck.eta = datetime.datetime.now() + datetime.timedelta(minutes=30)
                    
                    # Update client order status
                    from ..models import ClientOrder
                    order = db.query(ClientOrder).filter(
                        ClientOrder.assigned_truck_id == truck.truck_id,
                        ClientOrder.status == "LOADING"
                    ).first()
                    if order:
                        order.status = "EN_ROUTE"
                    
                    reason = f"Mission #{mission_id} completed. Company truck {truck.supplier} has been loaded and has departed for client delivery (Dock {dock_id} released)."
                    log_decision(db, "COMPANY_TRUCK_DEPART", reason)
                else:
                    # Supplier truck completed unloading!
                    truck.status = "COMPLETED"
                    reason = f"Mission #{mission_id} completed. Supplier truck {truck.supplier} has been unloaded and released (Dock {dock_id} released)."
                    log_decision(db, "SUPPLIER_TRUCK_RELEASE", reason)
                
                dock.status = "FREE"
                dock.current_truck = None
            
    db.commit()
    
    # MQTT Notifications
    mqtt_manager.publish("mission/completed", {"mission_id": mission_id, "status": "COMPLETED"})
    if robot:
        mqtt_manager.publish("robot/status", {"robot_id": robot.robot_id, "status": "AVAILABLE", "position": robot.position, "battery": robot.battery})
    if dock_id:
        mqtt_manager.publish("dock/status", {"dock_id": dock_id, "status": "FREE", "current_truck": None})
        
    # Check if there are queued trucks or arrived trucks waiting for robots
    # Let's process the queue
    process_waiting_jobs(db)

def process_waiting_jobs(db: Session):
    """Checks if there are queued trucks or arrived trucks waiting for robots, and schedules them."""
    # 0. First check for pending client orders and try to process them
    from ..models import ClientOrder
    pending_orders = db.query(ClientOrder).filter(ClientOrder.status == "PENDING").all()
    for order in pending_orders:
        res = process_single_client_order(db, order)
        if res:
            logger.info(f"Processed pending client order #{order.order_id}")
            break # Let other events cycle
    # 1. Process trucks that are ARRIVED or QUEUED
    waiting_trucks = db.query(Truck).filter(Truck.status.in_(["ARRIVED", "QUEUED"])).order_by(Truck.priority.desc()).all()
    
    for truck in waiting_trucks:
        # Check if it already has a dock assigned
        dock = db.query(Dock).filter(Dock.current_truck == truck.truck_id).first()
        
        if dock:
            # It already has a dock, just needs a robot
            robots = db.query(Robot).all()
            robot_scores = {}
            for r in robots:
                score = score_robot(r, dock.dock_id)
                if score > 0:
                    robot_scores[r.robot_id] = (r, score)
                    
            if robot_scores:
                selected_robot, score = max(robot_scores.values(), key=lambda x: x[1])
                first_zone = db.query(Zone).first()
                dock_zone_id = first_zone.zone_id if first_zone else 1
                
                # Find best storage zone
                zones = db.query(Zone).all()
                zone_scores = {}
                for zone in zones:
                    score_z = score_storage_zone(zone, truck.cargo_type, truck.operation_type)
                    if score_z > 0:
                        zone_scores[zone.zone_id] = (zone, score_z)
                        
                if zone_scores:
                    selected_zone, _ = max(zone_scores.values(), key=lambda x: x[1])
                    
                    # Assign robot
                    selected_robot.status = "BUSY"
                    truck.status = "PROCESSING"
                    
                    # Route logic
                    if truck.operation_type == "PICKUP":
                        mission_source = selected_zone.zone_id
                        mission_destination = dock_zone_id
                    else:
                        mission_source = dock_zone_id
                        mission_destination = selected_zone.zone_id

                    # Spawn Mission
                    mission = Mission(
                        robot_id=selected_robot.robot_id,
                        source_zone=mission_source,
                        destination_zone=mission_destination,
                        status="RUNNING",
                        operation_type=truck.operation_type,
                        truck_id=truck.truck_id
                    )
                    db.add(mission)
                    db.commit()
                    db.refresh(mission)
                    
                    # Adjust capacity
                    if truck.operation_type == "PICKUP":
                        selected_zone.occupied = max(0, selected_zone.occupied - 10)
                    else:
                        selected_zone.occupied = min(selected_zone.capacity, selected_zone.occupied + 10)
                    db.commit()
                    
                    reason = (f"Queued truck {truck.truck_id} waiting at Dock {dock.dock_id} has been processed. "
                              f"Robot {selected_robot.robot_id} assigned. Mission {mission.mission_id} ({truck.operation_type}) started.")
                    log_decision(db, "QUEUED_TRUCK_PROCESSED", reason)
                    
                    mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "PROCESSING"})
                    mqtt_manager.publish("robot/status", {"robot_id": selected_robot.robot_id, "status": "BUSY", "position": f"Zone_{mission_source}"})
                    mqtt_manager.publish("mission/create", {
                        "mission_id": mission.mission_id,
                        "robot_id": selected_robot.robot_id,
                        "source_zone": mission_source,
                        "destination_zone": mission_destination,
                        "status": "RUNNING",
                        "operation_type": truck.operation_type
                    })
                    break
        else:
            # Doesn't have a dock. Needs Zone, Dock, and Robot (JIT Allocation)
            zones = db.query(Zone).all()
            zone_scores = {}
            for zone in zones:
                score = score_storage_zone(zone, truck.cargo_type, truck.operation_type)
                if score > 0:
                    zone_scores[zone.zone_id] = (zone, score)
            if not zone_scores:
                continue
            selected_zone, _ = max(zone_scores.values(), key=lambda x: x[1])
            
            # Find free dock
            docks = db.query(Dock).all()
            dock_scores = {}
            for d in docks:
                score = score_dock(d, selected_zone.zone_id, truck.cargo_type)
                if score > 0:
                    dock_scores[d.dock_id] = (d, score)
                    
            if dock_scores:
                selected_dock, _ = max(dock_scores.values(), key=lambda x: x[1])
                first_zone = db.query(Zone).first()
                dock_zone_id = first_zone.zone_id if first_zone else 1
                
                # Check robot
                robots = db.query(Robot).all()
                robot_scores = {}
                for r in robots:
                    score = score_robot(r, selected_dock.dock_id)
                    if score > 0:
                        robot_scores[r.robot_id] = (r, score)
                        
                if robot_scores:
                    selected_robot, _ = max(robot_scores.values(), key=lambda x: x[1])
                    
                    # Assign resources
                    truck.status = "PROCESSING"
                    selected_dock.status = "OCCUPIED"
                    selected_dock.current_truck = truck.truck_id
                    selected_robot.status = "BUSY"
                    
                    # Route logic
                    if truck.operation_type == "PICKUP":
                        mission_source = selected_zone.zone_id
                        mission_destination = dock_zone_id
                    else:
                        mission_source = dock_zone_id
                        mission_destination = selected_zone.zone_id

                    mission = Mission(
                        robot_id=selected_robot.robot_id,
                        source_zone=mission_source,
                        destination_zone=mission_destination,
                        status="RUNNING",
                        operation_type=truck.operation_type,
                        truck_id=truck.truck_id
                    )
                    db.add(mission)
                    db.commit()
                    db.refresh(mission)
                    
                    if truck.operation_type == "PICKUP":
                        selected_zone.occupied = max(0, selected_zone.occupied - 10)
                    else:
                        selected_zone.occupied = min(selected_zone.capacity, selected_zone.occupied + 10)
                    db.commit()
                    
                    reason = (f"JIT Allocation: Arrived truck {truck.truck_id} assigned to Dock {selected_dock.dock_id} and Robot {selected_robot.robot_id}. "
                              f"Mission {mission.mission_id} ({truck.operation_type}) started.")
                    log_decision(db, "JIT_TRUCK_PROCESSED", reason)
                    
                    mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "PROCESSING"})
                    mqtt_manager.publish("dock/status", {"dock_id": selected_dock.dock_id, "status": "OCCUPIED", "current_truck": truck.truck_id})
                    mqtt_manager.publish("robot/status", {"robot_id": selected_robot.robot_id, "status": "BUSY", "position": f"Zone_{mission_source}"})
                    mqtt_manager.publish("mission/create", {
                        "mission_id": mission.mission_id,
                        "robot_id": selected_robot.robot_id,
                        "source_zone": mission_source,
                        "destination_zone": mission_destination,
                        "status": "RUNNING",
                        "operation_type": truck.operation_type
                    })
                else:
                    # Assign dock only, wait for robot
                    selected_dock.status = "OCCUPIED"
                    selected_dock.current_truck = truck.truck_id
                    truck.status = "ARRIVED"
                    db.commit()
                    
                    reason = f"JIT Allocation: Arrived truck {truck.truck_id} assigned to Dock {selected_dock.dock_id}, but no robots available. Waiting at dock."
                    log_decision(db, "JIT_TRUCK_ARRIVED_NO_ROBOT", reason)
                    
                    mqtt_manager.publish("dock/status", {"dock_id": selected_dock.dock_id, "status": "OCCUPIED", "current_truck": truck.truck_id})
                    mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "ARRIVED"})
                break

def select_best_company_truck(db: Session, cargo_type: str) -> Truck:
    # Find idle company trucks compatible with the cargo type
    idle_trucks = db.query(Truck).filter(
        Truck.is_company_truck == True,
        Truck.company_truck_status == "IDLE"
    ).all()
    
    # Try to find exact cargo match first
    for truck in idle_trucks:
        if truck.cargo_type == cargo_type:
            return truck
            
    # Fallback to general truck if no exact match
    for truck in idle_trucks:
        if truck.cargo_type == "General":
            return truck
            
    return None

def process_single_client_order(db: Session, order) -> dict:
    from ..models import Truck, Dock, Robot, Mission, Zone
    from .scoring import score_storage_zone, score_dock, score_robot
    
    # 1. Select best company truck
    truck = select_best_company_truck(db, order.cargo_type)
    if not truck:
        return None
        
    # 2. Select best Storage Zone for PICKUP (must have at least 10 units of cargo)
    zones = db.query(Zone).all()
    zone_scores = {}
    for zone in zones:
        score = score_storage_zone(zone, order.cargo_type, "PICKUP")
        if score > 0:
            zone_scores[zone.zone_id] = (zone, score)
            
    if not zone_scores:
        return None
        
    selected_zone, best_zone_score = max(zone_scores.values(), key=lambda x: x[1])
    
    # 3. Select free Dock
    docks = db.query(Dock).all()
    dock_scores = {}
    for d in docks:
        score = score_dock(d, selected_zone.zone_id, order.cargo_type)
        if score > 0:
            dock_scores[d.dock_id] = (d, score)
            
    if not dock_scores:
        return None
        
    selected_dock, best_dock_score = max(dock_scores.values(), key=lambda x: x[1])
    
    # 4. Select Robot (AGV)
    first_zone = db.query(Zone).first()
    dock_zone_id = first_zone.zone_id if first_zone else 1
    
    robots = db.query(Robot).all()
    robot_scores = {}
    for r in robots:
        score = score_robot(r, selected_dock.dock_id)
        if score > 0:
            robot_scores[r.robot_id] = (r, score)
            
    if not robot_scores:
        # Dock assigned, but no robot available: we will queue the loading mission
        selected_dock.status = "OCCUPIED"
        selected_dock.current_truck = truck.truck_id
        
        truck.company_truck_status = "LOADING"
        truck.status = "PROCESSING"
        truck.route_id = order.destination
        truck.gps_progress = 0.0
        
        order.status = "LOADING"
        order.assigned_truck_id = truck.truck_id
        db.commit()
        
        reason = (f"Client order #{order.order_id} matched. Company truck {truck.supplier} assigned to Dock {selected_dock.dock_id}. "
                  f"No AGVs available. Loading mission will start once a robot is free.")
        log_decision(db, "CLIENT_ORDER_MATCH_NO_ROBOT", reason)
        return {
            "status": "LOADING_WAITING_ROBOT",
            "order_id": order.order_id,
            "truck_id": truck.truck_id,
            "dock_id": selected_dock.dock_id,
            "reason": "Truck docked, waiting for robot to load."
        }
        
    selected_robot, best_robot_score = max(robot_scores.values(), key=lambda x: x[1])
    
    # 5. Spawn loading mission (PICKUP)
    selected_dock.status = "OCCUPIED"
    selected_dock.current_truck = truck.truck_id
    
    truck.company_truck_status = "LOADING"
    truck.status = "PROCESSING"
    truck.route_id = order.destination
    truck.gps_progress = 0.0
    
    selected_robot.status = "BUSY"
    
    order.status = "LOADING"
    order.assigned_truck_id = truck.truck_id
    
    mission = Mission(
        robot_id=selected_robot.robot_id,
        source_zone=selected_zone.zone_id,
        destination_zone=dock_zone_id,
        status="RUNNING",
        operation_type="PICKUP",
        truck_id=truck.truck_id
    )
    db.add(mission)
    db.commit()
    db.refresh(mission)
    
    # Adjust capacity (PICKUP from selected zone)
    selected_zone.occupied = max(0, selected_zone.occupied - 10)
    db.commit()
    
    reason = (f"Client order #{order.order_id} matched. Company truck {truck.supplier} assigned to Dock {selected_dock.dock_id} (Score: {best_dock_score:.1f}). "
              f"Cargo picked up from Zone {selected_zone.zone_id} ({selected_zone.product_type}, Score: {best_zone_score:.1f}). "
              f"Robot {selected_robot.robot_id} assigned (Score: {best_robot_score:.1f}). Mission {mission.mission_id} (PICKUP) started.")
    log_decision(db, "CLIENT_ORDER_MATCH", reason)
    
    # Publish MQTT statuses
    mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "PROCESSING", "company_truck_status": "LOADING"})
    mqtt_manager.publish("dock/status", {"dock_id": selected_dock.dock_id, "status": "OCCUPIED", "current_truck": truck.truck_id})
    mqtt_manager.publish("robot/status", {"robot_id": selected_robot.robot_id, "status": "BUSY", "position": f"Zone_{selected_zone.zone_id}"})
    mqtt_manager.publish("mission/create", {
        "mission_id": mission.mission_id,
        "robot_id": selected_robot.robot_id,
        "source_zone": selected_zone.zone_id,
        "destination_zone": dock_zone_id,
        "status": "RUNNING",
        "operation_type": "PICKUP"
    })
    
    return {
        "status": "LOADING",
        "order_id": order.order_id,
        "truck_id": truck.truck_id,
        "dock_id": selected_dock.dock_id,
        "robot_id": selected_robot.robot_id,
        "mission_id": mission.mission_id
    }

def create_client_order(
    db: Session,
    client_name: str,
    cargo_type: str,
    quantity: int,
    destination: str,
    priority: int = 3
) -> dict:
    from ..models import ClientOrder
    
    # Create client order
    order = ClientOrder(
        client_name=client_name,
        cargo_type=cargo_type,
        quantity=quantity,
        destination=destination,
        status="PENDING"
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Try to process the order immediately
    result = process_single_client_order(db, order)
    if result:
        return result
        
    return {
        "status": "PENDING",
        "order_id": order.order_id,
        "reason": "Order queued. No company trucks or docks available currently."
    }
