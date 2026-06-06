from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, CheckConstraint, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Truck(Base):
    __tablename__ = "trucks"

    truck_id = Column(Integer, primary_key=True, index=True)
    supplier = Column(String(255), nullable=False)
    cargo_type = Column(String(100))
    eta = Column(DateTime)
    priority = Column(Integer)
    status = Column(String(50), default="PENDING")
    origin = Column(String(100))
    operation_type = Column(String(50), default="DELIVERY")
    route_id = Column(String(50), default="Route_1")
    gps_progress = Column(Float, default=0.0)
    is_company_truck = Column(Boolean, default=False)
    company_truck_status = Column(String(50), default="IDLE")

    docks = relationship("Dock", back_populates="truck")

class ClientOrder(Base):
    __tablename__ = "client_orders"

    order_id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(255), nullable=False)
    cargo_type = Column(String(100))
    quantity = Column(Integer, default=10)
    destination = Column(String(255))
    status = Column(String(50), default="PENDING")
    assigned_truck_id = Column(Integer, ForeignKey("trucks.truck_id"))
    created_at = Column(DateTime, server_default=func.now())

    truck = relationship("Truck")

class Dock(Base):
    __tablename__ = "docks"

    dock_id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), default="FREE")
    current_truck = Column(Integer, ForeignKey("trucks.truck_id"))

    truck = relationship("Truck", back_populates="docks")

class Robot(Base):
    __tablename__ = "robots"

    robot_id = Column(Integer, primary_key=True, index=True)
    battery = Column(Integer, CheckConstraint('battery >= 0 AND battery <= 100'))
    position = Column(String(100))
    status = Column(String(50), default="AVAILABLE")

    missions = relationship("Mission", back_populates="robot")

class Zone(Base):
    __tablename__ = "zones"

    zone_id = Column(Integer, primary_key=True, index=True)
    capacity = Column(Integer)
    occupied = Column(Integer, default=0)
    product_type = Column(String(100))

    # Relationships for missions (source and destination)
    source_missions = relationship("Mission", foreign_keys="[Mission.source_zone]", back_populates="source")
    dest_missions = relationship("Mission", foreign_keys="[Mission.destination_zone]", back_populates="destination")

class Mission(Base):
    __tablename__ = "missions"

    mission_id = Column(Integer, primary_key=True, index=True)
    robot_id = Column(Integer, ForeignKey("robots.robot_id"))
    source_zone = Column(Integer, ForeignKey("zones.zone_id"))
    destination_zone = Column(Integer, ForeignKey("zones.zone_id"))
    status = Column(String(50), default="PENDING")
    operation_type = Column(String(50), default="DELIVERY")
    truck_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)

    robot = relationship("Robot", back_populates="missions")
    source = relationship("Zone", foreign_keys=[source_zone], back_populates="source_missions")
    destination = relationship("Zone", foreign_keys=[destination_zone], back_populates="dest_missions")

class DecisionLog(Base):
    __tablename__ = "decision_logs"

    decision_id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, server_default=func.now())
    decision_type = Column(String(100))
    decision_reason = Column(Text)
    agent_source = Column(String(50))

class Incident(Base):
    __tablename__ = "incidents"

    incident_id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String(50), nullable=False)
    incident_type = Column(String(50), nullable=False)
    delay_minutes = Column(Integer, default=0)
    active = Column(Boolean, default=True)
