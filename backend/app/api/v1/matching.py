from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.dependencies import get_current_user

router = APIRouter(tags=["Investor Matching"])

@router.post("/investors/{investor_id}/match", response_model=Dict[str, Any])
async def run_matching(investor_id: str, deal_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Matching engine not implemented yet")

@router.get("/deals/{deal_id}/matches", response_model=List[Dict[str, Any]])
async def list_matches(deal_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Matching engine not implemented yet")
