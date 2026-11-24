from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.dependencies import get_current_user

router = APIRouter(tags=["Data Rooms"])

@router.get("/data_rooms", response_model=List[Dict[str, Any]])
async def list_data_rooms(current_user=Depends(get_current_user)):
    # Placeholder implementation
    return []

@router.get("/data_rooms/{room_id}", response_model=Dict[str, Any])
async def get_data_room(room_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data room not found")

@router.post("/data_rooms", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_data_room(room: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.patch("/data_rooms/{room_id}", response_model=Dict[str, Any])
async def update_data_room(room_id: str, room: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.delete("/data_rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_data_room(room_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
