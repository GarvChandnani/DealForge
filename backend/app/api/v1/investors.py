from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.dependencies import get_current_user
from app.models.business import Investor
from app.schemas import InvestorCreate, InvestorRead, InvestorUpdate

router = APIRouter(tags=["Investors"])

@router.get("/investors", response_model=List[InvestorRead])
async def list_investors(skip: int = 0, limit: int = 100, current_user=Depends(get_current_user)):
    # TODO: add tenant scoping and actual DB query
    return []

@router.get("/investors/{investor_id}", response_model=InvestorRead)
async def get_investor(investor_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investor not found")

@router.post("/investors", response_model=InvestorRead, status_code=status.HTTP_201_CREATED)
async def create_investor(investor: InvestorCreate, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.patch("/investors/{investor_id}", response_model=InvestorRead)
async def update_investor(investor_id: str, investor: InvestorUpdate, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.delete("/investors/{investor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investor(investor_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
