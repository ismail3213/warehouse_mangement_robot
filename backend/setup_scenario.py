from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Truck, Dock, Robot, Zone, Mission, DecisionLog, Incident, ClientOrder
from app.agents.coordinator import log_decision
import datetime

def setup():
    db = SessionLocal()

    # 1. Reset everything using Postgres TRUNCATE to reset sequences
    from sqlalchemy import text
    db.execute(text("TRUNCATE TABLE client_orders, decision_logs, missions, docks, trucks, robots, zones, incidents RESTART IDENTITY CASCADE"))
    db.commit()

    # Reseed Docks, Zones, Robots
    docks = [Dock(status="FREE") for _ in range(4)]
    zones = [
        Zone(capacity=100, occupied=50, product_type="General"),
        Zone(capacity=80, occupied=50, product_type="Cold"),
        Zone(capacity=120, occupied=50, product_type="Hazardous"),
        Zone(capacity=150, occupied=50, product_type="General"),
        Zone(capacity=100, occupied=50, product_type="Electronics")
    ]
    robots = [
        Robot(battery=100, position="Zone_1", status="AVAILABLE"),
        Robot(battery=95, position="Zone_2", status="AVAILABLE"),
        Robot(battery=88, position="Zone_3", status="AVAILABLE"),
        Robot(battery=100, position="Zone_4", status="AVAILABLE")
    ]
    db.add_all(docks)
    db.add_all(zones)
    db.add_all(robots)
    db.commit()

    # Occupy 2 docks with supplier trucks (Docks 1 and 2 full)
    for i in range(2):
        t = Truck(supplier=f"Supplier {i+1}", cargo_type="General", priority=1, status="PROCESSING", operation_type="DELIVERY", route_id=f"Supplier_Route_{i+1}", is_company_truck=False, gps_progress=1.0, eta=datetime.datetime.now())
        db.add(t)
        db.commit()
        docks[i].status = "OCCUPIED"
        docks[i].current_truck = t.truck_id
        db.commit()
        
    # Now Docks 3 and 4 are free.

    # Create 3 Company Trucks heading to warehouse.
    # Truck A is fastest, should arrive first.
    truck_a = Truck(
        supplier="SWOS Fleet Alpha", cargo_type="General", is_company_truck=True,
        company_truck_status="EN_ROUTE_TO_WAREHOUSE", status="PROCESSING",
        gps_progress=0.85, eta=datetime.datetime.now() + datetime.timedelta(seconds=15),
        route_id="Route_1"
    )
    # Truck B is second.
    truck_b = Truck(
        supplier="SWOS Fleet Beta", cargo_type="General", is_company_truck=True,
        company_truck_status="EN_ROUTE_TO_WAREHOUSE", status="PROCESSING",
        gps_progress=0.80, eta=datetime.datetime.now() + datetime.timedelta(seconds=20),
        route_id="Route_2"
    )
    # Truck C is third.
    truck_c = Truck(
        supplier="SWOS Fleet Gamma", cargo_type="General", is_company_truck=True,
        company_truck_status="EN_ROUTE_TO_WAREHOUSE", status="PROCESSING",
        gps_progress=0.75, eta=datetime.datetime.now() + datetime.timedelta(seconds=25),
        route_id="Route_3"
    )
    db.add_all([truck_a, truck_b, truck_c])

    # Create 3 Client Orders waiting for these trucks
    orders = [
        ClientOrder(client_name="Order 1", cargo_type="General", quantity=10, destination="City North", status="PENDING"),
        ClientOrder(client_name="Order 2", cargo_type="General", quantity=10, destination="City South", status="PENDING"),
        ClientOrder(client_name="Order 3", cargo_type="General", quantity=10, destination="City West", status="PENDING")
    ]
    db.add_all(orders)

    # Log the setup
    log_decision(db, "SCENARIO_SETUP", "Scenario initialized: 2 docks full, 2 free. 3 company trucks inbound. 3 client orders pending.")

    db.commit()
    db.close()
    print("Scenario setup complete!")

if __name__ == "__main__":
    setup()
