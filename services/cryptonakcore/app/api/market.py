from fastapi import APIRouter
from app.services.market import set_market_price, get_market_price

router = APIRouter()

@router.post("/price/{value}")
def update_price(value: float):
    set_market_price(value)
    return {"new_market_price": value}

@router.get("/price")
def read_price():
    return {"market_price": get_market_price()}
