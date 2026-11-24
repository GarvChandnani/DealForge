# services/matching_engine.py
"""Investor matching engine service.
Implements deterministic scoring based on investor attributes and deal attributes.
Provides optional semantic similarity for investment thesis using sentence‑transformers.
"""

from typing import List, Dict, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.business import Investor, Deal, DealMatch
from sqlalchemy import and_

# Optional: sentence‑transformers for thesis similarity
try:
    from sentence_transformers import SentenceTransformer, util
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _semantic_enabled = True
except Exception:
    _semantic_enabled = False
    _model = None

# Weight configuration (default as per user choice)
WEIGHTS = {
    "sector": 30,
    "cheque": 20,
    "geography": 20,
    "stage": 15,
    "thesis": 15,
}

def _sector_score(deal_sectors: List[str], investor_sectors: List[str]) -> float:
    if not investor_sectors:
        return 0.0
    overlap = len(set(deal_sectors) & set(investor_sectors))
    return (overlap / len(investor_sectors)) * 100

def _cheque_score(deal_amount: Decimal, min_cheque: Decimal, max_cheque: Decimal) -> float:
    if min_cheque is None or max_cheque is None:
        return 0.0
    if min_cheque <= deal_amount <= max_cheque:
        return 100.0
    # distance based penalty
    diff = min(abs(deal_amount - min_cheque), abs(deal_amount - max_cheque))
    # simple linear scaling – if diff exceeds 50% of range, score 0
    range_span = max_cheque - min_cheque
    if range_span == 0:
        return 0.0
    penalty = (diff / (range_span * 0.5)) * 100
    return max(0.0, 100.0 - penalty)

def _geography_score(deal_geo: List[str], investor_geo: List[str]) -> float:
    if not investor_geo:
        return 0.0
    overlap = len(set(deal_geo) & set(investor_geo))
    return (overlap / len(investor_geo)) * 100

def _stage_score(deal_stage: str, investor_stage: str) -> float:
    if not investor_stage:
        return 0.0
    return 100.0 if deal_stage.lower() == investor_stage.lower() else 0.0

def _thesis_score(deal_thesis: str, investor_thesis: str) -> float:
    if not investor_thesis:
        return 0.0
    if not _semantic_enabled:
        # fallback: keyword overlap
        deal_words = set(deal_thesis.lower().split())
        inv_words = set(investor_thesis.lower().split())
        overlap = len(deal_words & inv_words)
        return (overlap / max(1, len(inv_words))) * 100
    # semantic similarity using embeddings
    embeddings = _model.encode([deal_thesis, investor_thesis], convert_to_tensor=True)
    sim = util.cos_sim(embeddings[0], embeddings[1]).item()
    return sim * 100  # convert to percentage

def calculate_match(deal: Deal, investor: Investor) -> Dict[str, Any]:
    """Calculate suitability score and detailed breakdown for a single investor."""
    # Extract fields – defaults to empty structures when missing
    deal_sectors = getattr(deal, "sector", []) or []
    inv_sectors = investor.preferred_sectors or []
    sector = _sector_score(deal_sectors, inv_sectors)

    deal_amount = getattr(deal, "funding_requirement", Decimal(0))
    cheque = _cheque_score(deal_amount, investor.investment_min, investor.investment_max)

    deal_geo = getattr(deal, "location", []) or []
    inv_geo = investor.geography or []
    geography = _geography_score(deal_geo, inv_geo)

    stage = _stage_score(getattr(deal, "investment_stage", ""), investor.investment_stage)

    thesis = _thesis_score(getattr(deal, "investment_thesis", ""), investor.thesis or "")

    # Weighted total (weights sum to 100)
    total = (
        sector * WEIGHTS["sector"]
        + cheque * WEIGHTS["cheque"]
        + geography * WEIGHTS["geography"]
        + stage * WEIGHTS["stage"]
        + thesis * WEIGHTS["thesis"]
    ) / 100.0

    # Build explanation and mismatch dictionaries
    criteria_match = {
        "sector": sector,
        "cheque": cheque,
        "geography": geography,
        "stage": stage,
        "thesis": thesis,
    }
    mismatches = {k: v for k, v in criteria_match.items() if v == 0}
    missing = {
        "sector": not bool(inv_sectors),
        "geography": not bool(inv_geo),
        "stage": not bool(investor.investment_stage),
        "thesis": not bool(investor.thesis),
    }
    missing = {k: v for k, v in missing.items() if v}

    explanation = (
        f"Sector compatibility {sector:.1f}%, "
        f"Cheque-size {cheque:.1f}%, "
        f"Geography {geography:.1f}%, "
        f"Stage {stage:.1f}%, "
        f"Thesis {thesis:.1f}%."
    )

    return {
        "investor_id": investor.id,
        "investor_name": investor.name,
        "score": round(total, 2),
        "explanation": explanation,
        "criteria_match": criteria_match,
        "mismatches": mismatches,
        "missing_info": missing,
    }

def match_deal_to_investors(db: Session, deal_id: str) -> List[Dict[str, Any]]:
    """Calculate matches for a deal and persist results in DealMatch table."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise ValueError(f"Deal {deal_id} not found")
    investors = db.query(Investor).all()
    results = []
    for inv in investors:
        match = calculate_match(deal, inv)
        # Upsert DealMatch record
        dm = (
            db.query(DealMatch)
            .filter(and_(DealMatch.deal_id == deal_id, DealMatch.investor_id == inv.id))
            .first()
        )
        if not dm:
            dm = DealMatch(
                deal_id=deal_id,
                investor_id=inv.id,
                match_score=Decimal(str(match["score"])),
                criteria_match=match["criteria_match"],
                mismatches=match["mismatches"],
                missing_info=match["missing_info"],
                status="suggested",
            )
            db.add(dm)
        else:
            dm.match_score = Decimal(str(match["score"]))
            dm.criteria_match = match["criteria_match"]
            dm.mismatches = match["mismatches"]
            dm.missing_info = match["missing_info"]
        results.append(match)
    db.commit()
    # Sort descending by score for convenience
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
