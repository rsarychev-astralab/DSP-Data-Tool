from fastapi import APIRouter, Query

from app.fl_address.core import lookup_fl_address

router = APIRouter(prefix="/api/fl-address", tags=["fl-address"])


@router.get("/lookup")
def fl_address_by_inn(
    inn: str = Query(..., min_length=10, max_length=20),
):
    return lookup_fl_address(inn)
