import os
import asyncio
import datetime
import logging
from typing import List
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .database import get_db, engine
from .models import Base, Truck, Dock, Robot, Zone, Mission, DecisionLog, Incident, ClientOrder
from .schemas import TruckSchema, DockSchema, RobotSchema, ZoneSchema, MissionSchema, DecisionLogSchema, SimulateTruckInput, IncidentSchema, IncidentToggle, DispatchBatchInput, ClientOrderSchema, SimulateClientOrderInput
from .agents.coordinator import orchestrate_truck_arrival, handle_mission_completion, predict_eta_minutes, log_decision, create_client_order
from .mqtt_client import mqtt_manager

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SWOS_Backend")

app = FastAPI(title="Smart Warehouse Orchestration System (SWOS) API")

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connection Manager for real-time dashboard updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        logger.info(f"Broadcasting event: {message.get('event', 'UNKNOWN')}")
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")

ws_manager = ConnectionManager()
main_loop = None

def broadcast_sync(event_data: dict):
    """Utility to broadcast events to WebSockets from background threads (like MQTT)"""
    if main_loop and ws_manager.active_connections:
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(event_data), main_loop)

# FastAPI lifespan event setup
@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    # Register MQTT callbacks
    mqtt_manager.register_callback("mission/completed", handle_mqtt_mission_completed)
    mqtt_manager.register_callback("robot/status", handle_mqtt_robot_status)
    mqtt_manager.register_callback("truck/arrival", handle_mqtt_truck_arrival)
    
    # Start MQTT client
    mqtt_manager.start()
    
    # Start GPS movement simulator loop
    asyncio.create_task(gps_movement_simulator())
    
    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    mqtt_manager.stop()
    logger.info("Application shutdown complete.")

# MQTT Callbacks routing back to DB + WebSockets
def handle_mqtt_mission_completed(payload):
    logger.info(f"MQTT callback triggered for mission/completed: {payload}")
    if isinstance(payload, dict) and "mission_id" in payload:
        # We need a new DB session since this runs in the MQTT background thread
        from .database import SessionLocal
        db = SessionLocal()
        try:
            handle_mission_completion(db, payload["mission_id"])
            # Broadcast state refresh to frontend
            broadcast_sync({"event": "STATE_UPDATE", "source": "MQTT_MISSION_COMPLETED"})
        except Exception as e:
            logger.error(f"Error handling mission completion callback: {e}")
        finally:
            db.close()

def handle_mqtt_robot_status(payload):
    logger.info(f"MQTT callback triggered for robot/status: {payload}")
    broadcast_sync({"event": "ROBOT_UPDATE", "data": payload})

def handle_mqtt_truck_arrival(payload):
    logger.info(f"MQTT callback triggered for truck/arrival: {payload}")
    broadcast_sync({"event": "STATE_UPDATE", "source": "MQTT_TRUCK_ARRIVAL"})

# Endpoints
@app.get("/api/state")
def get_global_state(db: Session = Depends(get_db)):
    """Fetch the complete state of the warehouse in a single API call"""
    trucks = db.query(Truck).order_by(Truck.truck_id.desc()).limit(50).all()
    docks = db.query(Dock).order_by(Dock.dock_id.asc()).all()
    robots = db.query(Robot).order_by(Robot.robot_id.asc()).all()
    zones = db.query(Zone).order_by(Zone.zone_id.asc()).all()
    missions = db.query(Mission).order_by(Mission.mission_id.desc()).limit(50).all()
    logs = db.query(DecisionLog).order_by(DecisionLog.decision_id.desc()).limit(100).all()
    incidents = db.query(Incident).all()
    client_orders = db.query(ClientOrder).order_by(ClientOrder.order_id.desc()).limit(50).all()
    
    # Check if XGBoost metadata is available
    model_stats = {}
    import json
    if os.path.exists("model_metrics.json"):
        try:
            with open("model_metrics.json", "r") as f:
                model_stats = json.load(f)
        except Exception:
            pass
            
    return {
        "trucks": [TruckSchema.model_validate(t) for t in trucks],
        "docks": [DockSchema.model_validate(d) for d in docks],
        "robots": [RobotSchema.model_validate(r) for r in robots],
        "zones": [ZoneSchema.model_validate(z) for z in zones],
        "missions": [MissionSchema.model_validate(m) for m in missions],
        "decision_logs": [DecisionLogSchema.model_validate(l) for l in logs],
        "incidents": [IncidentSchema.model_validate(i) for i in incidents],
        "client_orders": [ClientOrderSchema.model_validate(o) for o in client_orders],
        "model_stats": model_stats
    }

@app.post("/api/simulate/truck")
async def simulate_truck(input_data: SimulateTruckInput, db: Session = Depends(get_db)):
    """
    Trigger orchestration for a newly arrived truck.
    """
    try:
        res = orchestrate_truck_arrival(
            db=db,
            supplier=input_data.supplier,
            cargo_type=input_data.cargo_type,
            distance=input_data.distance,
            traffic_level=input_data.traffic_level,
            weather=input_data.weather,
            route_risk=input_data.route_risk,
            driver_fatigue=input_data.driver_fatigue,
            priority=input_data.priority
        )
        # Notify clients to reload data
        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "SIMULATED_ARRIVAL"})
        return res
    except Exception as e:
        logger.error(f"Error orchestrating simulated truck arrival: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/missions/{mission_id}/complete")
async def complete_mission(mission_id: int, db: Session = Depends(get_db)):
    """
    Simulate a robot completing its mission.
    In real usage, the robot publishes to 'mission/completed' via MQTT.
    """
    mission = db.query(Mission).filter(Mission.mission_id == mission_id).first()
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
        
    try:
        # Publish completed to MQTT
        mqtt_manager.publish("mission/completed", {"mission_id": mission_id, "status": "COMPLETED"})
        
        # Also run the local DB handling in case MQTT loop is delayed
        handle_mission_completion(db, mission_id)
        
        # Notify clients
        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "MANUAL_COMPLETION"})
        return {"status": "SUCCESS", "message": f"Mission {mission_id} marked as completed"}
    except Exception as e:
        logger.error(f"Error completing mission: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate/reset")
async def reset_simulation(db: Session = Depends(get_db)):
    """Reset the warehouse state back to initial seed data for testing"""
    try:
        # Truncate tables in order
        db.execute(Base.metadata.tables['decision_logs'].delete())
        db.execute(Base.metadata.tables['missions'].delete())
        db.execute(Base.metadata.tables['docks'].delete())
        db.execute(Base.metadata.tables['trucks'].delete())
        db.execute(Base.metadata.tables['robots'].delete())
        db.execute(Base.metadata.tables['zones'].delete())
        db.commit()
        
        # Re-seed
        docks = [Dock(status="FREE") for _ in range(4)]
        zones = [
            Zone(capacity=100, occupied=0, product_type="General"),
            Zone(capacity=80, occupied=0, product_type="Cold"),
            Zone(capacity=120, occupied=0, product_type="Hazardous"),
            Zone(capacity=150, occupied=0, product_type="General"),
            Zone(capacity=100, occupied=0, product_type="Electronics")
        ]
        robots = [
            Robot(battery=100, position="Zone_1", status="AVAILABLE"),
            Robot(battery=95, position="Zone_2", status="AVAILABLE"),
            Robot(battery=88, position="Zone_3", status="AVAILABLE")
        ]
        
        db.add_all(docks)
        db.add_all(zones)
        db.add_all(robots)
        db.add(DecisionLog(decision_type="SYSTEM_RESET", decision_reason="Warehouse simulation reset to default state", agent_source="System"))
        db.commit()
        
        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "SIMULATION_RESET"})
        return {"status": "SUCCESS", "message": "Simulation reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting simulation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket Route
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages if any (not needed for now)
            data = await websocket.receive_text()
            logger.info(f"Received message from WS client: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)

# Docks zone mapping
DOCK_TO_ZONE = {1: 1, 2: 2, 3: 3, 4: 4}

# GPS Simulator Background task
async def gps_movement_simulator():
    from .database import SessionLocal
    from .models import Truck, Mission, Incident, Dock, Robot
    from .agents.coordinator import log_decision, process_waiting_jobs
    from .mqtt_client import mqtt_manager

    logger.info("GPS movement simulator loop started.")
    while True:
        await asyncio.sleep(4)  # Update every 4 seconds
        db = SessionLocal()
        try:
            # Fetch all active trucks in transit (Supplier PENDING or Company moving)
            in_transit = db.query(Truck).filter(
                ((Truck.status == "PENDING") & (Truck.is_company_truck == False)) |
                ((Truck.is_company_truck == True) & (Truck.company_truck_status.in_(["EN_ROUTE_TO_CLIENT", "EN_ROUTE_TO_WAREHOUSE"])))
            ).all()
            
            if not in_transit:
                db.close()
                continue

            updated = False
            for truck in in_transit:
                # Default movement increment
                increment = 0.04
                
                # Check for active incidents on this route to apply slow-downs
                active_incidents = db.query(Incident).filter(Incident.route_id == truck.route_id, Incident.active == True).all()
                if active_incidents:
                    # Slower movement speed (4x) due to active road congestion/accident!
                    increment = 0.01

                truck.gps_progress = min(1.0, truck.gps_progress + increment)
                updated = True

                # If the truck reaches its destination (gps_progress == 1.0)
                if truck.gps_progress >= 1.0:
                    if truck.is_company_truck:
                        if truck.company_truck_status == "EN_ROUTE_TO_CLIENT":
                            from .models import ClientOrder
                            order = db.query(ClientOrder).filter(
                                ClientOrder.assigned_truck_id == truck.truck_id,
                                ClientOrder.status == "EN_ROUTE"
                            ).first()
                            if order:
                                order.status = "DELIVERED"
                            
                            truck.company_truck_status = "EN_ROUTE_TO_WAREHOUSE"
                            truck.gps_progress = 0.0
                            truck.eta = datetime.datetime.now() + datetime.timedelta(minutes=30)
                            
                            reason = f"Company truck {truck.supplier} has arrived at client. Order delivered. Starting return journey."
                            log_decision(db, "COMPANY_TRUCK_ARRIVED_CLIENT", reason)
                        elif truck.company_truck_status == "EN_ROUTE_TO_WAREHOUSE":
                            # Released from warehouse duty
                            truck.company_truck_status = "IDLE"
                            truck.status = "IDLE"
                            truck.gps_progress = 0.0
                            
                            reason = f"Company truck {truck.supplier} returned to warehouse and is now IDLE."
                            log_decision(db, "COMPANY_TRUCK_RETURNED", reason)
                            
                            process_waiting_jobs(db)
                    else:
                        # Inbound supplier truck arrival at warehouse
                        logger.info(f"Truck {truck.truck_id} ({truck.supplier}) has arrived at the warehouse via {truck.route_id}.")
                        
                        # With JIT Allocation, it DOES NOT have a dock assigned yet.
                        truck.status = "ARRIVED"
                        reason = f"Supplier truck #{truck.truck_id} ({truck.supplier}) arrived at warehouse. Entering queue for JIT resource allocation."
                        log_decision(db, "TRUCK_ARRIVED_JIT", reason)
                        mqtt_manager.publish("truck/status", {"truck_id": truck.truck_id, "status": "ARRIVED"})
                        
                        # Trigger queue processor immediately to allocate resources if available
                        process_waiting_jobs(db)

            if updated:
                db.commit()
                # Broadcast GPS updates
                broadcast_sync({"event": "STATE_UPDATE", "source": "GPS_UPDATER"})

        except Exception as e:
            logger.error(f"Error in GPS simulator loop: {e}")
        finally:
            db.close()

# New endpoints
@app.get("/api/incidents")
def get_incidents(db: Session = Depends(get_db)):
    """Fetch all road incidents"""
    incidents = db.query(Incident).all()
    return incidents

@app.post("/api/incidents/toggle")
async def toggle_incident(input_data: IncidentToggle, db: Session = Depends(get_db)):
    """Toggle an active road incident and trigger dynamic ETA recalculations"""
    try:
        incident = db.query(Incident).filter(
            Incident.route_id == input_data.route_id,
            Incident.incident_type == input_data.incident_type
        ).first()

        state_changed = False
        if incident:
            if incident.active != input_data.active:
                incident.active = input_data.active
                incident.delay_minutes = input_data.delay_minutes
                state_changed = True
        else:
            incident = Incident(
                route_id=input_data.route_id,
                incident_type=input_data.incident_type,
                delay_minutes=input_data.delay_minutes,
                active=input_data.active
            )
            db.add(incident)
            state_changed = True
        
        db.commit()
        db.refresh(incident)

        # Recalculate ETAs for all pending and en-route trucks on this route
        if state_changed:
            pending_trucks = db.query(Truck).filter(
                Truck.status.in_(["PENDING", "EN_ROUTE"]), 
                Truck.route_id == input_data.route_id
            ).all()

            adjustment = datetime.timedelta(minutes=input_data.delay_minutes) if input_data.active else -datetime.timedelta(minutes=input_data.delay_minutes)
            
            for truck in pending_trucks:
                truck.eta = truck.eta + adjustment
                state_str = "ACTIVATED" if input_data.active else "CLEARED"
                reason = f"Road incident '{input_data.incident_type}' {state_str} on route '{input_data.route_id}'. Recalculated ETA for Truck #{truck.truck_id} ({truck.supplier}): new arrival time {truck.eta.strftime('%H:%M:%S')} (+{input_data.delay_minutes}m)."
                log_decision(db, "INCIDENT_UPDATE", reason)

            db.commit()

        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "INCIDENT_TOGGLE"})
        return {"status": "SUCCESS", "incident": {"route_id": incident.route_id, "active": incident.active}}
    except Exception as e:
        logger.error(f"Error toggling incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate/dispatch")
async def dispatch_batch(input_data: DispatchBatchInput, db: Session = Depends(get_db)):
    """Simulate a batch of trucks dispatched together by a supplier"""
    results = []
    try:
        for t_input in input_data.trucks:
            res = orchestrate_truck_arrival(
                db=db,
                supplier=t_input.supplier,
                cargo_type=t_input.cargo_type,
                distance=t_input.distance,
                traffic_level=t_input.traffic_level,
                weather=t_input.weather,
                route_risk=t_input.route_risk,
                driver_fatigue=t_input.driver_fatigue,
                priority=t_input.priority,
                origin=t_input.origin,
                operation_type=t_input.operation_type,
                route_id=t_input.route_id
            )
            results.append(res)
        
        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "BATCH_DISPATCH"})
        return {"status": "SUCCESS", "results": results}
    except Exception as e:
        logger.error(f"Error in batch dispatch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/supplier/dispatch")
async def supplier_dispatch(input_data: SimulateTruckInput, db: Session = Depends(get_db)):
    """Simulate a supplier dispatching an inbound delivery truck (no GPS tracking)"""
    try:
        res = orchestrate_truck_arrival(
            db=db,
            supplier=input_data.supplier,
            cargo_type=input_data.cargo_type,
            distance=input_data.distance,
            traffic_level=input_data.traffic_level,
            weather=input_data.weather,
            route_risk=input_data.route_risk,
            driver_fatigue=input_data.driver_fatigue,
            priority=input_data.priority,
            origin=input_data.origin,
            operation_type="DELIVERY",
            route_id=input_data.route_id
        )
        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "SUPPLIER_DISPATCH"})
        return res
    except Exception as e:
        logger.error(f"Error in supplier dispatch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/client/order")
async def place_client_order(input_data: SimulateClientOrderInput, db: Session = Depends(get_db)):
    """Simulate placing a client order, triggering company truck matching and loading"""
    try:
        res = create_client_order(
            db=db,
            client_name=input_data.client_name,
            cargo_type=input_data.cargo_type,
            quantity=input_data.quantity,
            destination=input_data.destination,
            priority=input_data.priority
        )
        await ws_manager.broadcast({"event": "STATE_UPDATE", "source": "CLIENT_ORDER_PLACED"})
        return res
    except Exception as e:
        logger.error(f"Error placing client order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/client/orders")
def get_client_orders(db: Session = Depends(get_db)):
    """Fetch all client orders"""
    orders = db.query(ClientOrder).order_by(ClientOrder.order_id.desc()).all()
    return [ClientOrderSchema.model_validate(o) for o in orders]
