from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models import Order as OrderModel, Position as PositionModel

router = APIRouter()


# ---------- Pydantic models ----------

class OrderRequest(BaseModel):
    symbol: str
    side: str            # "long" / "short"
    qty: float
    entry_price: float   # prezzo di ingresso paper
    tp_price: float | None = None  # Take Profit
    sl_price: float | None = None  # Stop Loss
    order_type: str = "market"



class OrderResponse(BaseModel):
    id: int
    symbol: str
    side: str
    qty: float
    order_type: str
    tp_price: float | None
    sl_price: float | None
    status: str

    class Config:
        from_attributes = True


# ---------- Dependency DB ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Endpoints ----------

@router.post("/", response_model=OrderResponse)
async def create_order(order: OrderRequest, db: Session = Depends(get_db)):
    """
    Crea un ordine 'paper' nel DB
    e apre una posizione con lo stesso simbolo/side/qty/entry_price,
    propagando TP/SL.
    """

    # 1) salva l'ordine con TP/SL
    db_order = OrderModel(
        symbol=order.symbol,
        side=order.side,
        qty=order.qty,
        order_type=order.order_type,
        tp_price=order.tp_price,
        sl_price=order.sl_price,
        status="created",
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 2) crea anche una posizione aperta con TP/SL
    db_position = PositionModel(
        symbol=order.symbol,
        side=order.side,
        qty=order.qty,
        entry_price=order.entry_price,
        tp_price=order.tp_price,
        sl_price=order.sl_price,
        status="open",
    )
    db.add(db_position)
    db.commit()

    return db_order




@router.get("/", response_model=list[OrderResponse])
async def list_orders(db: Session = Depends(get_db)):
    """
    Restituisce tutti gli ordini (più recenti per primi).
    """
    orders = db.query(OrderModel).order_by(OrderModel.id.desc()).all()
    return orders
