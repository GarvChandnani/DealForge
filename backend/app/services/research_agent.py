import os
import json
from typing import List, Dict, Any
import requests
from decimal import Decimal
from sqlalchemy.orm import Session

# Optional semantic similarity using sentence_transformers
try:
    from sentence_transformers import SentenceTransformer, util
    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _semantic_enabled = True
except Exception:
    _semantic_enabled = False
    _model = None

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"  # title URL‑encoded
OPENCORPORATES_SEARCH = "https://api.opencorporates.com/v0.4/companies/search?q={query}"  # no API key needed for basic search

def _fetch_wikipedia(company_name: str) -> Dict[str, Any]:
    """Fetch Wikipedia summary for a company name. Returns a dict with keys `title`, `extract`, `source_url`."""
    try:
        resp = requests.get(WIKIPEDIA_API.format(title=requests.utils.quote(company_name)), timeout=5)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        return {
            "title": data.get("title"),
            "extract": data.get("extract"),
            "source_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        }
    except Exception:
        return {}

def _fetch_opencorporates(company_name: str) -> List[Dict[str, Any]]:
    """Search OpenCorporates for the company name. Returns a list of result dicts (basic fields)."""
    try:
        resp = requests.get(OPENCORPORATES_SEARCH.format(query=requests.utils.quote(company_name)), timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = data.get("results", {}).get("companies", [])
        cleaned = []
        for entry in results:
            comp = entry.get("company", {})
            cleaned.append({
                "name": comp.get("name"),
                "jurisdiction_code": comp.get("jurisdiction_code"),
                "company_number": comp.get("company_number"),
                "incorporation_date": comp.get("incorporation_date"),
                "source_url": comp.get("opencorporates_url"),
            })
        return cleaned
    except Exception:
        return []

def _semantic_opportunity_score(text: str, keywords: List[str]) -> float:
    if not _semantic_enabled or not keywords:
        return 0.0
    # Encode the full text and each keyword, compute max similarity
    embeddings = _model.encode([text] + keywords, convert_to_tensor=True)
    text_emb = embeddings[0]
    kw_embs = embeddings[1:]
    sims = util.cos_sim(text_emb, kw_embs).cpu().numpy().flatten()
    return float(max(sims) * 100)  # percentage

def _keyword_opportunity_score(text: str, keywords: List[str]) -> float:
    if not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return (matches / len(keywords)) * 100

def perform_research(
    db: Session,
    company_name: str,
    website: str | None,
    industry: str | None,
    keywords: List[str],
) -> Dict[str, Any]:
    """Main entry point for the Research Agent.

    Returns a dict containing:
        - summary: generated textual summary
        - sources: list of source dicts (title, url, excerpt)
        - verified_info: fields that came from a source
        - inference_info: AI‑generated parts not directly sourced
        - opportunities: list of identified opportunities (keyword + score)
    """
    # 1. Gather data from public sources
    wiki = _fetch_wikipedia(company_name)
    oc_results = _fetch_opencorporates(company_name)

    sources = []
    verified = {}
    inference = {}

    # Process Wikipedia
    if wiki:
        sources.append({"title": wiki.get("title"), "url": wiki.get("source_url"), "excerpt": wiki.get("extract")})
        verified["wikipedia_summary"] = wiki.get("extract")
    # Process OpenCorporates (use first result if any)
    if oc_results:
        first = oc_results[0]
        sources.append({"title": first.get("name"), "url": first.get("source_url"), "excerpt": f"Jurisdiction: {first.get('jurisdiction_code')}, Company No: {first.get('company_number')}"})
        verified["opencorporates"] = first

    # 2. Build deterministic fallback summary if no sources
    if not sources:
        # rule‑based template (fallback chosen by user)
        summary = f"{company_name} operates in the {industry or 'unspecified'} industry. Website: {website or 'N/A'}. No public data could be retrieved, so this summary is based on the provided inputs."
        inference["summary"] = summary
        return {
            "summary": summary,
            "sources": [],
            "verified_info": {},
            "inference_info": inference,
            "opportunities": [],
        }

    # 3. Generate a human‑readable summary
    parts = []
    if wiki.get("extract"):
        parts.append(wiki["extract"])
    if oc_results:
        oc = oc_results[0]
        parts.append(f"Company number {oc.get('company_number')} registered in {oc.get('jurisdiction_code')}.")
    summary = " ".join(parts).strip()

    # 4. Identify opportunities
    opportunities = []
    if summary:
        # Choose similarity method based on config (semantic enabled)
        if _semantic_enabled:
            score = _semantic_opportunity_score(summary, keywords)
        else:
            score = _keyword_opportunity_score(summary, keywords)
        if score > 0:
            opportunities.append({"type": "summary_match", "score": round(score, 2), "keywords": keywords})
    # 5. Assemble result dict
    result = {
        "summary": summary,
        "sources": sources,
        "verified_info": verified,
        "inference_info": inference,
        "opportunities": opportunities,
    }
    return result
