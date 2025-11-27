import asyncio
from fastapi import FastAPI
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.oms import auto_close_positions


async def position_watcher():
    """Loop infinito per controllare le posizioni ogni 1 secondo."""
    while True:
        db: Session = SessionLocal()
        try:
            auto_close_positions(db)
        finally:
            db.close()

        await asyncio.sleep(1)  # 1 secondo


def start_scheduler(app: FastAPI):

    @app.on_event("startup")
    async def start_background_tasks():
        asyncio.create_task(position_watcher())
