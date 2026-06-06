import os
import random
import datetime
import psycopg2
from dotenv import load_dotenv

# Load env variables
load_dotenv()

db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/swos")

# Parse connection params
try:
    clean_url = db_url.replace("postgresql://", "")
    credentials, rest = clean_url.split("@")
    user, password = credentials.split(":")
    host_port, db_name = rest.split("/")
    host, port = host_port.split(":")
except Exception:
    user, password, host, port, db_name = "postgres", "postgres", "localhost", "5432", "swos"

# Seeding parameters
SUPPLIERS = [
    "Amazon Logistics", "DHL Express", "FedEx Supply Chain", 
    "Geodis France", "Kuehne + Nagel", "DB Schenker", 
    "Maersk Logistics", "XPO Logistics", "Ceva Logistics"
]

CARGO_TYPES = ["General", "Cold", "Hazardous", "Electronics"]
CARGO_PROPORTIONS = [0.4, 0.2, 0.15, 0.25]  # General: 40%, Cold: 20%, Hazardous: 15%, Electronics: 25%

ZONE_COMPATIBILITY = {
    "General": [1, 4],
    "Cold": [2],
    "Hazardous": [3],
    "Electronics": [5]
}

DOCK_TO_ZONE = {1: 1, 2: 2, 3: 3, 4: 4}

ROUTE_ORIGINS = {
    "Route_1": "North Hub",
    "Route_2": "West Port",
    "Route_3": "South Depot",
    "Route_4": "East Warehouse"
}

def seed_history():
    print("Connecting to PostgreSQL to seed operational history...")
    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=db_name
        )
        cursor = conn.cursor()
        
        # Clear existing dynamic data (but keep zones, docks, and robots baseline)
        print("Clearing existing trucks, missions, and decision logs...")
        cursor.execute("TRUNCATE client_orders, decision_logs, missions, trucks RESTART IDENTITY CASCADE;")
        
        # Re-seed docks since they were cascade-truncated by trucks truncate
        print("Re-seeding Docks...")
        docks = [
            ("FREE", None),
            ("FREE", None),
            ("FREE", None),
            ("FREE", None)
        ]
        cursor.executemany("INSERT INTO docks (status, current_truck) VALUES (%s, %s)", docks)
        
        # Reset robots and zones to default statuses
        cursor.execute("UPDATE robots SET status = 'AVAILABLE', battery = 100, position = 'Zone_1';")
        cursor.execute("UPDATE zones SET occupied = 0;")
        conn.commit()
        
        # We will generate history for the past 5 days
        now = datetime.datetime.now()
        start_time = now - datetime.timedelta(days=5)
        
        # We will simulate 60 trucks arriving over these 5 days
        print("Simulating historical operations...")
        
        current_time = start_time
        truck_id_counter = 1
        mission_id_counter = 1
        
        # Keep track of simulated state of robots to make history consistent
        # Robot positions and battery levels
        robot_states = {
            1: {"position": 1, "battery": 100},
            2: {"position": 2, "battery": 95},
            3: {"position": 3, "battery": 88}
        }
        
        # Zone occupancies
        zone_occupancies = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        
        # List of events to insert at the end
        trucks_to_insert = []
        missions_to_insert = []
        logs_to_insert = []
        
        # Add system init log
        logs_to_insert.append((
            start_time - datetime.timedelta(minutes=10),
            "SYSTEM_INIT",
            "Warehouse management system initialized.",
            "System"
        ))
        
        while current_time < now - datetime.timedelta(hours=4):
            # Advance time randomly by 1 to 3 hours for each new truck arrival
            current_time += datetime.timedelta(hours=random.randint(1, 3), minutes=random.randint(0, 59))
            
            if current_time >= now - datetime.timedelta(hours=4):
                break
                
            supplier = random.choice(SUPPLIERS)
            cargo_type = random.choices(CARGO_TYPES, weights=CARGO_PROPORTIONS, k=1)[0]
            priority = random.randint(1, 5)
            
            # Predict ETA (ETA is departure + 1-4 hours)
            trip_duration_mins = random.randint(45, 180)
            eta_time = current_time + datetime.timedelta(minutes=trip_duration_mins)
            
            # The truck will arrive at current_time + trip_duration_mins
            arrival_time = eta_time
            
            route_id = random.choice(list(ROUTE_ORIGINS.keys()))
            origin = ROUTE_ORIGINS[route_id]
            op_type = random.choice(["DELIVERY", "PICKUP"])
            
            # We insert the truck as COMPLETED because it belongs to the past
            trucks_to_insert.append((
                truck_id_counter,
                supplier,
                cargo_type,
                eta_time,
                priority,
                "COMPLETED",
                origin,
                op_type,
                route_id,
                1.0 # progress completed
            ))
            
            # 1. Decision logic simulation: Select Zone
            compatible_zones = ZONE_COMPATIBILITY.get(cargo_type, [1, 4])
            # Select zone with least occupancy
            selected_zone_id = compatible_zones[0]
            if len(compatible_zones) > 1:
                # Pick the one with less occupancy
                selected_zone_id = min(compatible_zones, key=lambda z: zone_occupancies[z])
                
            # 2. Select Dock (randomly free dock at arrival time)
            selected_dock_id = random.randint(1, 4)
            source_zone_id = DOCK_TO_ZONE[selected_dock_id]
            
            # 3. Select Robot (pick one with highest battery or random)
            selected_robot_id = random.randint(1, 3)
            r_state = robot_states[selected_robot_id]
            
            # Record decision log for routing
            routing_reason = (
                f"Optimized routing complete. Truck #{truck_id_counter} ({supplier}) docked at Dock {selected_dock_id} (Score: {random.randint(140,175)}.0). "
                f"Cargo allocated to Zone {selected_zone_id} ({cargo_type}, Score: {random.randint(130,170)}.0). "
                f"Robot {selected_robot_id} assigned (Score: {random.randint(135,195)}.0). Mission #{mission_id_counter} started."
            )
            logs_to_insert.append((
                arrival_time,
                "ROUTING_SUCCESS",
                routing_reason,
                "Coordinator"
            ))
            
            # Mission duration
            mission_duration_mins = random.randint(15, 35)
            completion_time = arrival_time + datetime.timedelta(minutes=mission_duration_mins)
            
            # Add mission
            missions_to_insert.append((
                mission_id_counter,
                selected_robot_id,
                source_zone_id,
                selected_zone_id,
                "COMPLETED",
                arrival_time,
                completion_time
            ))
            
            # Update simulated state of robot
            battery_depletion = random.randint(8, 15)
            r_state["battery"] = max(15, r_state["battery"] - battery_depletion)
            r_state["position"] = f"Zone_{selected_zone_id}"
            
            # If robot battery is low, simulate a recharge event later
            if r_state["battery"] < 30:
                recharge_time = completion_time + datetime.timedelta(minutes=5)
                r_state["battery"] = 100
                logs_to_insert.append((
                    recharge_time,
                    "ROBOT_CHARGING",
                    f"Robot {selected_robot_id} battery low ({r_state['battery']}%). Automatically routed to charging station. Battery restored to 100%.",
                    "RobotAgent"
                ))
            
            # Update zone occupancy
            zone_occupancies[selected_zone_id] = min(100, zone_occupancies[selected_zone_id] + 10)
            
            # Record completion log
            completion_reason = (
                f"Mission #{mission_id_counter} completed successfully. Robot {selected_robot_id} is now at Zone_{selected_zone_id} "
                f"with {r_state['battery']}% battery. Dock {selected_dock_id} and Truck #{truck_id_counter} released."
            )
            logs_to_insert.append((
                completion_time,
                "MISSION_COMPLETED",
                completion_reason,
                "Coordinator"
            ))
            
            # Increment counters
            truck_id_counter += 1
            mission_id_counter += 1
            
        # Perform SQL inserts
        print(f"Inserting {len(trucks_to_insert)} completed trucks...")
        cursor.executemany(
            "INSERT INTO trucks (truck_id, supplier, cargo_type, eta, priority, status, origin, operation_type, route_id, gps_progress) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            trucks_to_insert
        )
        
        print(f"Inserting {len(missions_to_insert)} completed missions...")
        cursor.executemany(
            "INSERT INTO missions (mission_id, robot_id, source_zone, destination_zone, status, created_at, completed_at) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            missions_to_insert
        )
        
        print(f"Inserting {len(logs_to_insert)} decision log entries...")
        cursor.executemany(
            "INSERT INTO decision_logs (timestamp, decision_type, decision_reason, agent_source) VALUES (%s, %s, %s, %s)",
            logs_to_insert
        )
        
        # Apply final state of robots and zones to DB so it looks active
        print("Setting final state for robots and zones in DB...")
        for r_id, r_state in robot_states.items():
            cursor.execute(
                "UPDATE robots SET battery = %s, position = %s WHERE robot_id = %s",
                (r_state["battery"], f"Zone_{r_state['position']}", r_id)
            )
            
        for z_id, z_occ in zone_occupancies.items():
            cursor.execute(
                "UPDATE zones SET occupied = %s WHERE zone_id = %s",
                (z_occ, z_id)
            )
            
        # Add 1 active processing truck at the end to demonstrate a live dashboard state
        active_truck_id = truck_id_counter
        active_mission_id = mission_id_counter
        active_eta = now + datetime.timedelta(minutes=45)
        
        cursor.execute(
            "INSERT INTO trucks (truck_id, supplier, cargo_type, eta, priority, status, origin, operation_type, route_id, gps_progress) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (active_truck_id, "FedEx Supply Chain", "Cold", active_eta, 4, "PROCESSING", "West Port", "DELIVERY", "Route_2", 0.45)
        )
        
        cursor.execute("UPDATE docks SET status = 'OCCUPIED', current_truck = %s WHERE dock_id = 2", (active_truck_id,))
        cursor.execute("UPDATE robots SET status = 'BUSY', position = 'Zone_2' WHERE robot_id = 2")
        
        cursor.execute(
            "INSERT INTO missions (mission_id, robot_id, source_zone, destination_zone, status, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (active_mission_id, 2, 2, 2, "RUNNING", now)
        )
        
        cursor.execute(
            "INSERT INTO decision_logs (timestamp, decision_type, decision_reason, agent_source) VALUES (%s, %s, %s, %s)",
            (
                now, 
                "ROUTING_SUCCESS", 
                f"Optimized routing complete. Truck #{active_truck_id} (FedEx Supply Chain) docked at Dock 2 (Score: 172.0). Cargo allocated to Zone 2 (Cold, Score: 170.0). Robot 2 assigned (Score: 195.0). Mission #{active_mission_id} started.",
                "Coordinator"
            )
        )
        
        # Seed 3 company trucks
        print("Inserting 3 company-owned trucks...")
        company_trucks = [
            (active_truck_id + 1, "Company Truck Alpha", "General", 5, "IDLE", True, "IDLE"),
            (active_truck_id + 2, "Company Truck Beta", "Cold", 5, "IDLE", True, "IDLE"),
            (active_truck_id + 3, "Company Truck Gamma", "Hazardous", 5, "IDLE", True, "IDLE")
        ]
        cursor.executemany("INSERT INTO trucks (truck_id, supplier, cargo_type, priority, company_truck_status, is_company_truck, status) VALUES (%s, %s, %s, %s, %s, %s, %s)", company_trucks)
        
        # Reset sequence generators to avoid UniqueViolation errors on subsequent inserts
        print("Resetting database sequence generators...")
        cursor.execute("SELECT setval('trucks_truck_id_seq', COALESCE((SELECT MAX(truck_id) FROM trucks), 1));")
        cursor.execute("SELECT setval('missions_mission_id_seq', COALESCE((SELECT MAX(mission_id) FROM missions), 1));")
        cursor.execute("SELECT setval('decision_logs_decision_id_seq', COALESCE((SELECT MAX(decision_id) FROM decision_logs), 1));")
        cursor.execute("SELECT setval('docks_dock_id_seq', COALESCE((SELECT MAX(dock_id) FROM docks), 1));")
        cursor.execute("SELECT setval('robots_robot_id_seq', COALESCE((SELECT MAX(robot_id) FROM robots), 1));")
        cursor.execute("SELECT setval('zones_zone_id_seq', COALESCE((SELECT MAX(zone_id) FROM zones), 1));")
        cursor.execute("SELECT setval('client_orders_order_id_seq', COALESCE((SELECT MAX(order_id) FROM client_orders), 1));")
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Historical database seeding completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error seeding historical data: {e}")
        return False

if __name__ == "__main__":
    seed_history()
