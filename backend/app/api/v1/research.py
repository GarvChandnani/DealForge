from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_db
from app.services.research_agent import perform_research
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

class ResearchRequest(BaseModel):
    company_name: str = Field(..., description="Company name to research")
    website: Optional[str] = Field(None, description="Website URL (optional)")
    industry: Optional[str] = Field(None, description="Industry (optional)")
    keywords: List[str] = Field(default_factory=list, description="Research keywords")

@router.post("/research", response_model=dict)
def research_company(request: ResearchRequest, db: Session = Depends(get_db)):
    """Run the Research Agent and return a structured result."""
    try:
        result = perform_research(
            db=db,
            company_name=request.company_name,
            website=request.website,
            industry=request.industry,
            keywords=request.keywords,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
