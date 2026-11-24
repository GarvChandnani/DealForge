from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any

from app.dependencies import get_current_user

router = APIRouter(tags=["Documents"])

@router.get("/documents", response_model=List[Dict[str, Any]])
async def list_documents(current_user=Depends(get_current_user)):
    # Placeholder implementation
    return []

@router.get("/documents/{doc_id}", response_model=Dict[str, Any])
async def get_document(doc_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

@router.post("/documents", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_document(doc: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.patch("/documents/{doc_id}", response_model=Dict[str, Any])
async def update_document(doc_id: str, doc: Dict[str, Any], current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(doc_id: str, current_user=Depends(get_current_user)):
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
