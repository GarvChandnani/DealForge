"""LangGraph workflow for source-grounded deal and mandate generation."""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Literal, TypedDict
from zipfile import BadZipFile

from docx import Document as WordDocument
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError, PdfStreamError

from agents.llm.litellm_client import LLMClient
from agents.schemas.mandate_generation import (
    DealProposal,
    DocumentExtraction,
    FactConflict,
    FieldEvidence,
    FinancialAnalysis,
    QualityReview,
    SourceReference,
)

FACT_LABELS: dict[str, tuple[str, ...]] = {
    "company_name": ("company name", "company", "borrower", "business name"),
    "industry": ("industry",),
    "sector": ("sector",),
    "deal_type": ("deal type", "transaction type", "financing type"),
    "transaction_size": ("transaction size", "deal size", "transaction value"),
    "revenue": ("revenue", "annual revenue", "net sales"),
    "ebitda": ("ebitda", "adjusted ebitda"),
    "liabilities": ("liabilities", "total liabilities"),
    "assets": ("assets", "total assets"),
    "profitability": ("profitability", "net income", "net profit", "operating profit"),
    "funding_requirement": (
        "funding requirement",
        "funding sought",
        "capital sought",
        "capital required",
        "financing requirement",
    ),
    "target_valuation": ("target valuation", "valuation"),
}
FINANCIAL_FIELDS = (
    "revenue",
    "ebitda",
    "liabilities",
    "assets",
    "profitability",
    "funding_requirement",
)


class MandateGenerationState(TypedDict, total=False):
    source_document_id: str
    source_file_name: str
    source_content: bytes
    source_text: str
    source_type: Literal["pdf", "docx"]
    mode: Literal["mock", "litellm"]
    extraction: dict[str, Any]
    financial_analysis: dict[str, Any]
    deal_proposal: dict[str, Any]
    mandate_draft: str
    teaser_draft: str
    quality_review: dict[str, Any]
    agent_history: list[dict[str, Any]]


class DocumentProcessingError(ValueError):
    """A safe, user-correctable source-document processing error."""


class _LLMFact(BaseModel):
    value: str | None = None
    quote: str | None = None
    location: str | None = None


class _LLMExtraction(BaseModel):
    facts: dict[str, _LLMFact]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _history(
    state: MandateGenerationState, agent: str, summary: str
) -> list[dict[str, Any]]:
    return [
        *state.get("agent_history", []),
        {
            "agent": agent,
            "status": "completed",
            "summary": summary,
            "mode": state["mode"],
            "completed_at": _now(),
        },
    ]


def is_mock_mode() -> bool:
    """Use deterministic processing unless a provider key is configured."""
    if os.getenv("AI_MOCK_MODE", "").strip().casefold() in {"1", "true", "yes", "on"}:
        return True
    credential_names = (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "AZURE_API_KEY",
        "COHERE_API_KEY",
        "MISTRAL_API_KEY",
    )
    return not any(os.getenv(name) for name in credential_names)


def extract_document_text(
    file_name: str, content: bytes
) -> tuple[Literal["pdf", "docx"], list[tuple[str, str]]]:
    """Extract text with page/paragraph locations retained for citations."""
    suffix = os.path.splitext(file_name)[1].lower()
    lines: list[tuple[str, str]] = []
    if suffix == ".pdf":
        try:
            reader = PdfReader(BytesIO(content))
        except (PdfReadError, PdfStreamError) as exc:
            raise DocumentProcessingError("The PDF file could not be read.") from exc
        if reader.is_encrypted:
            raise DocumentProcessingError(
                "Password-protected PDF files are not supported."
            )
        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            lines.extend(
                (f"page {page_number}", line.strip())
                for line in page_text.splitlines()
                if line.strip()
            )
        return "pdf", lines
    if suffix == ".docx":
        try:
            document = WordDocument(BytesIO(content))
        except BadZipFile as exc:
            raise DocumentProcessingError("The DOCX file could not be read.") from exc
        for paragraph_number, paragraph in enumerate(document.paragraphs, start=1):
            if paragraph.text.strip():
                lines.append((f"paragraph {paragraph_number}", paragraph.text.strip()))
        for table_number, table in enumerate(document.tables, start=1):
            for row_number, row in enumerate(table.rows, start=1):
                row_text = " | ".join(cell.text.strip() for cell in row.cells).strip()
                if row_text:
                    lines.append((f"table {table_number}, row {row_number}", row_text))
        return "docx", lines
    raise DocumentProcessingError("Only PDF and DOCX source documents are supported.")


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _unavailable() -> FieldEvidence:
    return FieldEvidence(value=None, status="unavailable", source=None)


def _mock_extract(
    state: MandateGenerationState,
    lines: list[tuple[str, str]],
    document_type: Literal["pdf", "docx"],
) -> DocumentExtraction:
    facts: dict[str, FieldEvidence] = {
        field: _unavailable() for field in FACT_LABELS
    }
    matches: dict[str, list[tuple[str, str, str]]] = {
        field: [] for field in FACT_LABELS
    }
    labels = {
        re.sub(r"\s+", " ", label).casefold(): field
        for field, aliases in FACT_LABELS.items()
        for label in aliases
    }
    for location, line in lines:
        match = re.match(r"^\s*([^:=]+?)\s*[:=]\s*(.+?)\s*$", line)
        if not match:
            continue
        label = re.sub(r"\s+", " ", match.group(1).strip()).casefold()
        field = labels.get(label)
        if field:
            matches[field].append((match.group(2).strip(), location, line))

    conflicts: list[FactConflict] = []
    for field, entries in matches.items():
        if not entries:
            continue
        value, location, quote = entries[0]
        facts[field] = FieldEvidence(
            value=value,
            status="available",
            source=SourceReference(
                document_id=state["source_document_id"],
                file_name=state["source_file_name"],
                location=location,
                quote=quote,
            ),
        )
        distinct_values = list(dict.fromkeys(entry[0] for entry in entries))
        if len(distinct_values) > 1:
            conflicts.append(
                FactConflict(
                    field=field,
                    values=distinct_values,
                    sources=[
                        SourceReference(
                            document_id=state["source_document_id"],
                            file_name=state["source_file_name"],
                            location=entry[1],
                            quote=entry[2],
                        )
                        for entry in entries
                    ],
                )
            )
    return DocumentExtraction(
        source_document_id=state["source_document_id"],
        source_file_name=state["source_file_name"],
        document_type=document_type,
        text_length=len(state["source_text"]),
        facts=facts,
        conflicts=conflicts,
    )


async def _llm_extract(
    state: MandateGenerationState,
    document_type: Literal["pdf", "docx"],
) -> DocumentExtraction:
    client = LLMClient(temperature=0)
    fields = ", ".join(FACT_LABELS)
    raw = await client.chat(
        [
            {
                "role": "system",
                "content": (
                    "Extract only facts explicitly stated in the supplied document. "
                    "For every available fact, copy its exact source line into quote "
                    "and give its page/paragraph location. Do not infer, calculate, "
                    "or normalize figures. For absent fields return null value, quote, "
                    "and location. Return a JSON object with a facts object keyed by: "
                    f"{fields}. Each fact has value, quote, and location."
                ),
            },
            {
                "role": "user",
                "content": state["source_text"][:100_000],
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=4096,
    )
    extracted = _LLMExtraction.model_validate_json(raw)
    facts: dict[str, FieldEvidence] = {}
    source_lines: list[tuple[str, str]] = []
    for line in state["source_text"].splitlines():
        match = re.match(r"^\[([^\]]+)\]\s*(.*)$", line)
        if match:
            source_lines.append((match.group(1), match.group(2)))
    for field in FACT_LABELS:
        fact = extracted.facts.get(field)
        if fact is None or fact.value is None or not fact.value.strip():
            facts[field] = _unavailable()
            continue
        source = None
        matching_line = next(
            (
                (location, quote)
                for location, quote in source_lines
                if fact.quote
                and _normalized(quote) == _normalized(fact.quote)
            ),
            None,
        )
        if matching_line:
            source = SourceReference(
                document_id=state["source_document_id"],
                file_name=state["source_file_name"],
                location=matching_line[0],
                quote=matching_line[1],
            )
        facts[field] = FieldEvidence(
            value=fact.value.strip(),
            status="available",
            source=source,
        )
    return DocumentExtraction(
        source_document_id=state["source_document_id"],
        source_file_name=state["source_file_name"],
        document_type=document_type,
        text_length=len(state["source_text"]),
        facts=facts,
    )


async def document_extraction_agent(
    state: MandateGenerationState,
) -> dict[str, Any]:
    document_type, lines = extract_document_text(
        state["source_file_name"], state["source_content"]
    )
    source_text = "\n".join(f"[{location}] {line}" for location, line in lines)
    if not source_text:
        raise DocumentProcessingError(
            "No selectable text could be extracted. Scanned documents require OCR."
        )
    if len(source_text) > 200_000:
        source_text = source_text[:200_000]
    prepared_state = {**state, "source_text": source_text}
    extraction = (
        await _llm_extract(prepared_state, document_type)
        if state["mode"] == "litellm"
        else _mock_extract(prepared_state, lines, document_type)
    )
    return {
        "source_text": source_text,
        "extraction": extraction.model_dump(mode="json"),
        "agent_history": _history(
            state,
            "Document Extraction Agent",
            f"Extracted {len(lines)} text lines and retained source locations.",
        ),
    }


async def financial_analysis_agent(
    state: MandateGenerationState,
) -> dict[str, Any]:
    extraction = DocumentExtraction.model_validate(state["extraction"])
    analysis = FinancialAnalysis(
        **{
            field: extraction.facts.get(field, _unavailable())
            for field in FINANCIAL_FIELDS
        }
    )
    return {
        "financial_analysis": analysis.model_dump(mode="json"),
        "agent_history": _history(
            state,
            "Financial Analysis Agent",
            "Mapped documented financials; absent figures remain unavailable.",
        ),
    }


async def deal_structuring_agent(
    state: MandateGenerationState,
) -> dict[str, Any]:
    extraction = DocumentExtraction.model_validate(state["extraction"])
    financials = FinancialAnalysis.model_validate(state["financial_analysis"])
    facts = extraction.facts
    company_name = facts.get("company_name", _unavailable())
    title = (
        f"{company_name.value} financing opportunity"
        if company_name.status == "available" and company_name.value
        else "Confidential financing opportunity"
    )
    proposal = DealProposal(
        title=title,
        company_name=company_name,
        industry=facts.get("industry", _unavailable()),
        sector=facts.get("sector", _unavailable()),
        deal_type=facts.get("deal_type", _unavailable()),
        transaction_size=facts.get("transaction_size", _unavailable()),
        revenue=financials.revenue,
        ebitda=financials.ebitda,
        liabilities=financials.liabilities,
        assets=financials.assets,
        profitability=financials.profitability,
        funding_requirement=financials.funding_requirement,
        target_valuation=facts.get("target_valuation", _unavailable()),
        description=(
            "Structured from the supplied source document only. "
            "No external company or financial information has been added."
        ),
        source_document_id=extraction.source_document_id,
    )
    return {
        "deal_proposal": proposal.model_dump(mode="json"),
        "agent_history": _history(
            state,
            "Deal Structuring Agent",
            "Created a deal proposal using only cited source facts.",
        ),
    }


def _field_line(label: str, fact: FieldEvidence) -> str:
    if fact.status != "available" or not fact.value:
        return f"{label}: Unavailable"
    citation = ""
    if fact.source:
        citation = f" [Source: {fact.source.file_name}, {fact.source.location}]"
    return f"{label}: {fact.value}{citation}"


def _teaser_field_line(label: str, fact: FieldEvidence) -> str:
    if fact.status != "available" or not fact.value:
        return f"{label}: Unavailable"
    return f"{label}: {fact.value}"


async def mandate_generation_agent(
    state: MandateGenerationState,
) -> dict[str, Any]:
    proposal = DealProposal.model_validate(state["deal_proposal"])
    draft = "\n".join(
        [
            "DRAFT FINANCIAL MANDATE",
            proposal.title,
            "",
            "Client and transaction",
            _field_line("Company", proposal.company_name),
            _field_line("Industry", proposal.industry),
            _field_line("Sector", proposal.sector),
            _field_line("Deal type", proposal.deal_type),
            _field_line("Transaction size", proposal.transaction_size),
            _field_line("Funding requirement", proposal.funding_requirement),
            _field_line("Target valuation", proposal.target_valuation),
            "",
            "Financial information",
            _field_line("Revenue", proposal.revenue),
            _field_line("EBITDA", proposal.ebitda),
            _field_line("Assets", proposal.assets),
            _field_line("Liabilities", proposal.liabilities),
            _field_line("Profitability", proposal.profitability),
            "",
            "Scope",
            "Evaluate financing options based on the information supplied by the client.",
            "",
            "Draft only. Subject to human approval and legal review.",
            f"Source document ID: {proposal.source_document_id}",
        ]
    )
    return {
        "mandate_draft": draft,
        "agent_history": _history(
            state,
            "Mandate Generation Agent",
            "Prepared an editable mandate draft with unavailable fields disclosed.",
        ),
    }


async def teaser_generation_agent(
    state: MandateGenerationState,
) -> dict[str, Any]:
    proposal = DealProposal.model_validate(state["deal_proposal"])
    category = (
        proposal.sector.value
        if proposal.sector.status == "available" and proposal.sector.value
        else proposal.industry.value
        if proposal.industry.status == "available" and proposal.industry.value
        else "company"
    )
    teaser = "\n".join(
        [
            f"CONFIDENTIAL {category.upper()} OPPORTUNITY",
            "Company identity withheld for investor circulation.",
            "",
            _teaser_field_line("Industry", proposal.industry),
            _teaser_field_line("Sector", proposal.sector),
            _teaser_field_line("Deal type", proposal.deal_type),
            _teaser_field_line("Funding requirement", proposal.funding_requirement),
            _teaser_field_line("Revenue", proposal.revenue),
            _teaser_field_line("EBITDA", proposal.ebitda),
            "",
            "Additional financial details are unavailable unless stated above.",
            "Draft only. Human approval is required before circulation.",
        ]
    )
    company_name = proposal.company_name.value
    if company_name and company_name.casefold() in teaser.casefold():
        teaser = teaser.replace(company_name, "[REDACTED]")
    return {
        "teaser_draft": teaser,
        "agent_history": _history(
            state,
            "Teaser Generation Agent",
            "Prepared an anonymized teaser from documented facts only.",
        ),
    }


async def quality_review_agent(
    state: MandateGenerationState,
) -> dict[str, Any]:
    extraction = DocumentExtraction.model_validate(state["extraction"])
    proposal = DealProposal.model_validate(state["deal_proposal"])
    source_text = _normalized(state["source_text"])
    unsupported: list[str] = []
    evidence_fields = {
        **extraction.facts,
        "proposal.transaction_size": proposal.transaction_size,
        "proposal.target_valuation": proposal.target_valuation,
    }
    for name, fact in evidence_fields.items():
        if fact.status != "available":
            continue
        if (
            fact.source is None
            or fact.source.document_id != extraction.source_document_id
            or not fact.source.quote
            or _normalized(fact.source.quote) not in source_text
            or not fact.value
            or _normalized(fact.value) not in _normalized(fact.source.quote)
        ):
            unsupported.append(name)

    missing = [
        name
        for name in ("company_name", "industry", "sector", *FINANCIAL_FIELDS)
        if (
            extraction.facts.get(name, _unavailable()).status == "unavailable"
        )
    ]
    contradictions = [conflict.field for conflict in extraction.conflicts]
    report = QualityReview(
        missing_fields=missing,
        contradictions=contradictions,
        unsupported_claims=unsupported,
        passed=not unsupported and not contradictions,
    )
    return {
        "quality_review": report.model_dump(mode="json"),
        "agent_history": _history(
            state,
            "Quality Review Agent",
            (
                "Reviewed source support, missing data, and conflicting values."
                if report.passed
                else "Flagged unsupported claims or conflicting source values."
            ),
        ),
    }


def build_mandate_generation_graph():
    """Build the six-agent graph; each node returns validated Pydantic output."""
    graph = StateGraph(MandateGenerationState)
    graph.add_node("extract_document", document_extraction_agent)
    graph.add_node("analyze_financials", financial_analysis_agent)
    graph.add_node("structure_deal", deal_structuring_agent)
    graph.add_node("draft_mandate", mandate_generation_agent)
    graph.add_node("draft_teaser", teaser_generation_agent)
    graph.add_node("review_quality", quality_review_agent)
    graph.add_edge(START, "extract_document")
    graph.add_edge("extract_document", "analyze_financials")
    graph.add_edge("analyze_financials", "structure_deal")
    graph.add_edge("structure_deal", "draft_mandate")
    graph.add_edge("draft_mandate", "draft_teaser")
    graph.add_edge("draft_teaser", "review_quality")
    graph.add_edge("review_quality", END)
    return graph.compile()


mandate_generation_graph = build_mandate_generation_graph()
