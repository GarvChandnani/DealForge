from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.dependencies import get_current_user

router = APIRouter(tags=["Transactions"])

@router.get("/transactions", response_model=List[Dict[str, Any]])
async def list_transactions(current_user=Depends(get_current_user)):
    # Placeholder implementation
    return []

@router.get("/transactions/{tx_id}", response_model=Dict[str, Any])
async def get_transaction(tx_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

@router.post("/transactions", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_transaction(tx: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.patch("/transactions/{tx_id}", response_model=Dict[str, Any])
async def update_transaction(tx_id: str, tx: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.delete("/transactions/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(tx_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
