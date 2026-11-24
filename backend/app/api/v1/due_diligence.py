from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.dependencies import get_current_user

router = APIRouter(tags=["Due Diligence"])

@router.get("/due_diligence", response_model=List[Dict[str, Any]])
async def list_due_diligence(current_user=Depends(get_current_user)):
    # Placeholder implementation
    return []

@router.get("/due_diligence/{dd_id}", response_model=Dict[str, Any])
async def get_due_diligence(dd_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Due diligence entry not found")

@router.post("/due_diligence", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_due_diligence(entry: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.patch("/due_diligence/{dd_id}", response_model=Dict[str, Any])
async def update_due_diligence(dd_id: str, entry: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.delete("/due_diligence/{dd_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_due_diligence(dd_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
