from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TruckBase(BaseModel):
    supplier: str
    cargo_type: Optional[str] = None
    eta: Optional[datetime] = None
    priority: Optional[int] = None
    status: Optional[str] = "PENDING"
    origin: Optional[str] = None
    operation_type: Optional[str] = "DELIVERY"
    route_id: Optional[str] = "Route_1"
    gps_progress: Optional[float] = 0.0
    is_company_truck: Optional[bool] = False
    company_truck_status: Optional[str] = "IDLE"

class TruckCreate(TruckBase):
    pass

class TruckSchema(TruckBase):
    truck_id: int

    class Config:
        from_attributes = True

class ClientOrderBase(BaseModel):
    client_name: str
    cargo_type: str
    quantity: Optional[int] = 10
    destination: str
    status: Optional[str] = "PENDING"
    assigned_truck_id: Optional[int] = None

class ClientOrderCreate(ClientOrderBase):
    pass

class ClientOrderSchema(ClientOrderBase):
    order_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class DockBase(BaseModel):
    status: str = "FREE"
    current_truck: Optional[int] = None

class DockSchema(DockBase):
    dock_id: int

    class Config:
        from_attributes = True

class RobotBase(BaseModel):
    battery: int
    position: str
    status: str = "AVAILABLE"

class RobotSchema(RobotBase):
    robot_id: int

    class Config:
        from_attributes = True

class ZoneBase(BaseModel):
    capacity: int
    occupied: int = 0
    product_type: str

class ZoneSchema(ZoneBase):
    zone_id: int

    class Config:
        from_attributes = True

class MissionBase(BaseModel):
    robot_id: Optional[int] = None
    source_zone: int
    destination_zone: int
    status: str = "PENDING"
    operation_type: str = "DELIVERY"
    truck_id: Optional[int] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class MissionCreate(BaseModel):
    robot_id: int
    source_zone: int
    destination_zone: int

class MissionSchema(MissionBase):
    mission_id: int

    class Config:
        from_attributes = True

class DecisionLogSchema(BaseModel):
    decision_id: int
    timestamp: datetime
    decision_type: str
    decision_reason: str
    agent_source: str

    class Config:
        from_attributes = True

# Simulation input
class SimulateTruckInput(BaseModel):
    supplier: str
    cargo_type: str
    distance: float
    traffic_level: int  # 0: Low, 1: Medium, 2: High
    weather: int        # 0: Sunny, 1: Rainy, 2: Stormy
    route_risk: int     # 0: Low, 1: Medium, 2: High
    driver_fatigue: int # 0: No, 1: Yes
    priority: int       # 1 to 5 (higher is more critical)
    origin: Optional[str] = "North Hub"
    operation_type: Optional[str] = "DELIVERY"
    route_id: Optional[str] = "Route_1"

# Incident Schemas
class IncidentBase(BaseModel):
    route_id: str
    incident_type: str
    delay_minutes: int
    active: bool = True

class IncidentCreate(IncidentBase):
    pass

class IncidentSchema(IncidentBase):
    incident_id: int

    class Config:
        from_attributes = True

class IncidentToggle(BaseModel):
    route_id: str
    incident_type: str
    delay_minutes: int
    active: bool

# Batch Dispatch
class DispatchedTruckItem(BaseModel):
    supplier: str
    cargo_type: str
    distance: float
    traffic_level: int
    weather: int
    route_risk: int
    driver_fatigue: int
    priority: int
    origin: str
    operation_type: str
    route_id: str

class DispatchBatchInput(BaseModel):
    supplier: str
    trucks: List[DispatchedTruckItem]

class SimulateClientOrderInput(BaseModel):
    client_name: str
    cargo_type: str
    destination: str
    quantity: Optional[int] = 10
    priority: Optional[int] = 3
