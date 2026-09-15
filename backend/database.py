from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import inspect, text

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_URL = f"sqlite:///{BASE_DIR / 'sat_sa.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def initialize_database():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    migrations = {
        'entities': [('risk_level', "ALTER TABLE entities ADD COLUMN risk_level VARCHAR DEFAULT 'Critical'")],
        'findings': [
            ('finding_type', "ALTER TABLE findings ADD COLUMN finding_type VARCHAR DEFAULT 'operational_control'"),
            ('priority', "ALTER TABLE findings ADD COLUMN priority VARCHAR DEFAULT 'P2'"),
            ('description', "ALTER TABLE findings ADD COLUMN description TEXT DEFAULT ''"),
            ('detection_method', "ALTER TABLE findings ADD COLUMN detection_method TEXT DEFAULT ''"),
            ('affected_assets', "ALTER TABLE findings ADD COLUMN affected_assets TEXT DEFAULT '[]'"),
            ('affected_cases', "ALTER TABLE findings ADD COLUMN affected_cases TEXT DEFAULT '[]'"),
            ('evidence_ids', "ALTER TABLE findings ADD COLUMN evidence_ids TEXT DEFAULT '[]'"),
            ('metrics', "ALTER TABLE findings ADD COLUMN metrics TEXT DEFAULT '{}'"),
            ('recommendation', "ALTER TABLE findings ADD COLUMN recommendation TEXT DEFAULT ''"),
            ('ai_generated', "ALTER TABLE findings ADD COLUMN ai_generated BOOLEAN DEFAULT 0"),
        ],
        'dimension_scores': [('weight', "ALTER TABLE dimension_scores ADD COLUMN weight FLOAT DEFAULT 0"), ('contribution', "ALTER TABLE dimension_scores ADD COLUMN contribution FLOAT DEFAULT 0")],
    }
    with engine.begin() as connection:
        for table, columns in migrations.items():
            existing = {column['name'] for column in inspect(engine).get_columns(table)}
            for name, statement in columns:
                if name not in existing:
                    connection.execute(text(statement))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
