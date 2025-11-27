from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Base per tutti i modelli ORM (models.py la importerà da qui)
Base = declarative_base()

# Se usi SQLite, serve il flag check_same_thread=False
connect_args = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Crea l'engine collegato al database
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

# Factory delle sessioni
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
