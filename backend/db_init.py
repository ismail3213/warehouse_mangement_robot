import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load env variables
load_dotenv()

db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/swos")

# Parse connection params for admin connection
# Extract base connection (to 'postgres' default database)
try:
    # Parse URL: postgresql://username:password@host:port/database
    clean_url = db_url.replace("postgresql://", "")
    credentials, rest = clean_url.split("@")
    user, password = credentials.split(":")
    host_port, db_name = rest.split("/")
    host, port = host_port.split(":")
except Exception as e:
    print(f"Error parsing DATABASE_URL: {e}")
    # Fallbacks
    user, password, host, port, db_name = "postgres", "postgres", "localhost", "5432", "swos"

def init_db():
    print(f"Connecting to PostgreSQL as admin (user: {user}) to check for database '{db_name}'...")
    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database="postgres"
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating it...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")
        print("Please check that your PostgreSQL service is running and credentials are correct.")
        return False

    print(f"Connecting to database '{db_name}'...")
    try:
        conn = psycopg2.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=db_name
        )
        cursor = conn.cursor()
        
        # Read init.sql
        init_sql_path = os.path.join(os.path.dirname(__file__), "..", "init.sql")
        print(f"Reading schema from {init_sql_path}...")
        with open(init_sql_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        print("Executing schema...")
        cursor.execute(schema_sql)
        conn.commit()
        print("Tables created successfully.")
        
        # Seed initial data
        # 1. Docks
        print("Seeding Docks...")
        cursor.execute("SELECT COUNT(*) FROM docks")
        if cursor.fetchone()[0] == 0:
            docks = [
                ("FREE", None),
                ("FREE", None),
                ("FREE", None),
                ("FREE", None)
            ]
            cursor.executemany("INSERT INTO docks (status, current_truck) VALUES (%s, %s)", docks)
            print("Docks seeded.")
        else:
            print("Docks already seeded.")
            
        # 2. Zones
        print("Seeding Zones...")
        cursor.execute("SELECT COUNT(*) FROM zones")
        if cursor.fetchone()[0] == 0:
            zones = [
                (100, 0, "General"),
                (80, 0, "Cold"),
                (120, 0, "Hazardous"),
                (150, 0, "General"),
                (100, 0, "Electronics")
            ]
            cursor.executemany("INSERT INTO zones (capacity, occupied, product_type) VALUES (%s, %s, %s)", zones)
            print("Zones seeded.")
        else:
            print("Zones already seeded.")
            
        # 3. Robots
        print("Seeding Robots...")
        cursor.execute("SELECT COUNT(*) FROM robots")
        if cursor.fetchone()[0] == 0:
            robots = [
                (100, "Zone_1", "AVAILABLE"),
                (95, "Zone_2", "AVAILABLE"),
                (88, "Zone_3", "AVAILABLE")
            ]
            cursor.executemany("INSERT INTO robots (battery, position, status) VALUES (%s, %s, %s)", robots)
            print("Robots seeded.")
        else:
            print("Robots already seeded.")
            
        # 3.5. Company Trucks
        print("Seeding Company Trucks...")
        cursor.execute("SELECT COUNT(*) FROM trucks WHERE is_company_truck = TRUE")
        if cursor.fetchone()[0] == 0:
            company_trucks = [
                ("Company Truck Alpha", "General", 5, "IDLE", True, "IDLE"),
                ("Company Truck Beta", "Cold", 5, "IDLE", True, "IDLE"),
                ("Company Truck Gamma", "Hazardous", 5, "IDLE", True, "IDLE")
            ]
            cursor.executemany("INSERT INTO trucks (supplier, cargo_type, priority, company_truck_status, is_company_truck, status) VALUES (%s, %s, %s, %s, %s, %s)", company_trucks)
            print("Company Trucks seeded.")
        else:
            print("Company Trucks already seeded.")
            
        # 4. Initial Decision Log entry
        cursor.execute("INSERT INTO decision_logs (decision_type, decision_reason, agent_source) VALUES (%s, %s, %s)",
                       ("SYSTEM_INIT", "Database initialized and resources seeded successfully", "System"))
        conn.commit()
        
        cursor.close()
        conn.close()
        print("Database initialization completed successfully!")
        return True
    except Exception as e:
        print(f"Error executing schema or seeding data: {e}")
        return False

if __name__ == "__main__":
    init_db()
