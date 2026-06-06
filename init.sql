-- Drop tables if they exist (for clean re-initialization)
DROP TABLE IF EXISTS client_orders CASCADE;
DROP TABLE IF EXISTS decision_logs CASCADE;
DROP TABLE IF EXISTS missions CASCADE;
DROP TABLE IF EXISTS zones CASCADE;
DROP TABLE IF EXISTS robots CASCADE;
DROP TABLE IF EXISTS docks CASCADE;
DROP TABLE IF EXISTS trucks CASCADE;
DROP TABLE IF EXISTS incidents CASCADE;

-- Create trucks table
CREATE TABLE trucks (
    truck_id SERIAL PRIMARY KEY,
    supplier VARCHAR(255) NOT NULL,
    cargo_type VARCHAR(100),
    eta TIMESTAMP,
    priority INTEGER,
    status VARCHAR(50) DEFAULT 'PENDING',
    origin VARCHAR(100),
    operation_type VARCHAR(50) DEFAULT 'DELIVERY',
    route_id VARCHAR(50) DEFAULT 'Route_1',
    gps_progress REAL DEFAULT 0.0,
    is_company_truck BOOLEAN DEFAULT FALSE,
    company_truck_status VARCHAR(50) DEFAULT 'IDLE'
);

-- Create client_orders table
CREATE TABLE client_orders (
    order_id SERIAL PRIMARY KEY,
    client_name VARCHAR(255) NOT NULL,
    cargo_type VARCHAR(100),
    quantity INTEGER DEFAULT 10,
    destination VARCHAR(255),
    status VARCHAR(50) DEFAULT 'PENDING',
    assigned_truck_id INTEGER REFERENCES trucks(truck_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create docks table
CREATE TABLE docks (
    dock_id SERIAL PRIMARY KEY,
    status VARCHAR(50) DEFAULT 'FREE',
    current_truck INTEGER REFERENCES trucks(truck_id)
);

-- Create robots table
CREATE TABLE robots (
    robot_id SERIAL PRIMARY KEY,
    battery INTEGER CHECK (battery >= 0 AND battery <= 100),
    position VARCHAR(100),
    status VARCHAR(50) DEFAULT 'AVAILABLE'
);

-- Create zones table
CREATE TABLE zones (
    zone_id SERIAL PRIMARY KEY,
    capacity INTEGER,
    occupied INTEGER DEFAULT 0,
    product_type VARCHAR(100)
);

-- Create missions table
CREATE TABLE missions (
    mission_id SERIAL PRIMARY KEY,
    robot_id INTEGER REFERENCES robots(robot_id),
    source_zone INTEGER REFERENCES zones(zone_id),
    destination_zone INTEGER REFERENCES zones(zone_id),
    status VARCHAR(50) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Create decision_logs table
CREATE TABLE decision_logs (
    decision_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    decision_type VARCHAR(100),
    decision_reason TEXT,
    agent_source VARCHAR(50)
);

-- Create incidents table
CREATE TABLE incidents (
    incident_id SERIAL PRIMARY KEY,
    route_id VARCHAR(50) NOT NULL,
    incident_type VARCHAR(50) NOT NULL,
    delay_minutes INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE
);