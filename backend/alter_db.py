from app.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    conn.execute(text('ALTER TABLE missions ADD COLUMN IF NOT EXISTS truck_id INTEGER NULL;'))
    conn.commit()
    print('Altered missions table')
