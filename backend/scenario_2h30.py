from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import SessionLocal, engine
from app.models import Base, Truck, Dock, Robot, Zone, Mission, DecisionLog, Incident, ClientOrder
from app.agents.coordinator import log_decision
import datetime

def setup():
    db = SessionLocal()

    # 1. Reset everything
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

    # Occupy 3 docks with phantom supplier trucks
    supplier_names = ["DHL Express", "FedEx", "UPS"]
    for i in range(3):
        t = Truck(supplier=supplier_names[i], cargo_type="General", priority=1, status="PROCESSING", operation_type="DELIVERY", route_id=f"Supplier_Route_{i+1}", is_company_truck=False, gps_progress=1.0, eta=datetime.datetime.now())
        db.add(t)
        db.commit()
        docks[i].status = "OCCUPIED"
        docks[i].current_truck = t.truck_id
        robots[i].status = "BUSY"
        m = Mission(robot_id=robots[i].robot_id, source_zone=1, destination_zone=zones[i].zone_id, status="RUNNING", operation_type="DELIVERY", truck_id=t.truck_id)
        db.add(m)
        db.commit()
        
    # Now Dock 4 is free.

    # 1 Supplier Truck arriving in 2 hours (progress 0.8)
    truck_supp = Truck(
        supplier="Kuehne + Nagel", cargo_type="General", priority=2, status="PENDING", operation_type="DELIVERY",
        route_id="Route_1", is_company_truck=False, gps_progress=0.80, 
        eta=datetime.datetime.now() + datetime.timedelta(hours=2)
    )
    
    # 3 Company Trucks arriving at different times
    truck_comp1 = Truck(
        supplier="waremind_01", cargo_type="General", is_company_truck=True,
        company_truck_status="EN_ROUTE_TO_WAREHOUSE", status="EN_ROUTE",
        gps_progress=0.01, eta=datetime.datetime.now() + datetime.timedelta(hours=2, minutes=30),
        route_id="Route_2"
    )
    truck_comp2 = Truck(
        supplier="waremind_02", cargo_type="General", is_company_truck=True,
        company_truck_status="EN_ROUTE_TO_WAREHOUSE", status="EN_ROUTE",
        gps_progress=0.05, eta=datetime.datetime.now() + datetime.timedelta(hours=3, minutes=0),
        route_id="Route_3"
    )
    truck_comp3 = Truck(
        supplier="waremind_03", cargo_type="General", is_company_truck=True,
        company_truck_status="EN_ROUTE_TO_WAREHOUSE", status="EN_ROUTE",
        gps_progress=0.01, eta=datetime.datetime.now() + datetime.timedelta(hours=4, minutes=0),
        route_id="Route_4"
    )
    
    db.add_all([truck_supp, truck_comp1, truck_comp2, truck_comp3])

    # Create 3 Client Orders waiting
    orders = [
        ClientOrder(client_name="Client A", cargo_type="General", quantity=10, destination="City North", status="PENDING"),
        ClientOrder(client_name="Client B", cargo_type="General", quantity=10, destination="City South", status="PENDING"),
        ClientOrder(client_name="Client C", cargo_type="General", quantity=10, destination="City East", status="PENDING")
    ]
    db.add_all(orders)

    # Log the setup
    log_decision(db, "SCENARIO_SETUP", "Scenario 2h30 initialized: 3 docks full, 1 free. Supplier in 2h, Company in 2h30. 2 client orders pending.")

    db.commit()
    db.close()
    print("Scenario 2h30 setup complete!")

if __name__ == "__main__":
    setup()
