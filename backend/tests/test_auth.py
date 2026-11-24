from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from docx import Document as WordDocument
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

REPOSITORY_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_DIR))

from app.api.router import api_router
from app.config import get_settings
from app.db.session import get_db
from app.errors import register_error_handlers
from app.models import Base
from agents.llm.litellm_client import LLMClient

EXPECTED_TENANT_TABLES = {
    "users",
    "organizations",
    "originators",
    "clients",
    "deals",
    "investors",
    "documents",
    "deal_matches",
    "mandates",
    "compliance_records",
    "transactions",
    "activity_logs",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SECRET_KEY", "test-only-signing-key-not-for-production")
    get_settings.cache_clear()

    database_path = tmp_path / "dealforge-test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}",
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def create_schema() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = FastAPI()
    app.include_router(api_router)
    register_error_handlers(app)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())
    get_settings.cache_clear()


def register(client: TestClient, email: str, organization: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": organization,
            "full_name": "Fictional Test User",
            "email": email,
            "password": "Correct Horse Battery 42!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def authorization(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sample_docx(lines: list[str]) -> bytes:
    document = WordDocument()
    for line in lines:
        document.add_paragraph(line)
    content = BytesIO()
    document.save(content)
    return content.getvalue()


def _sample_pdf(lines: list[str]) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font_reference}
            )
        }
    )
    commands = ["BT /F1 12 Tf 72 720 Td"]
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj 0 -18 Td")
    commands.append("ET")
    stream = DecodedStreamObject()
    stream.set_data("\n".join(commands).encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    content = BytesIO()
    writer.write(content)
    return content.getvalue()


def test_tenant_schema_entities() -> None:
    assert EXPECTED_TENANT_TABLES.issubset(Base.metadata.tables)
    for table_name in EXPECTED_TENANT_TABLES - {"organizations"}:
        assert "organization_id" in Base.metadata.tables[table_name].columns


def test_registration_and_login(client: TestClient) -> None:
    result = register(client, "alice@example.com", "Fictional Alpha")

    assert result["user"]["role"] == "admin"
    assert result["user"]["organization_id"] == result["organization"]["id"]
    assert result["access_token"]

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "Correct Horse Battery 42!"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == result["user"]["id"]


def test_invalid_credentials_are_rejected(client: TestClient) -> None:
    register(client, "alice@example.com", "Fictional Alpha")

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "not-the-password"},
    )
    assert response.status_code == 401


def test_invalid_and_expired_tokens_are_rejected(client: TestClient) -> None:
    invalid = client.get(
        "/api/v1/auth/me",
        headers=authorization("not-a-jwt"),
    )
    assert invalid.status_code == 401

    expired_token = jwt.encode(
        {
            "sub": "fictional-user-id",
            "org": "fictional-organization-id",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        "test-only-signing-key-not-for-production",
        algorithm="HS256",
    )
    expired = client.get(
        "/api/v1/auth/me",
        headers=authorization(expired_token),
    )
    assert expired.status_code == 401


def test_profile_and_protected_endpoint_access(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/contacts/").status_code == 401

    result = register(client, "alice@example.com", "Fictional Alpha")
    headers = authorization(result["access_token"])
    profile = client.get("/api/v1/auth/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["email"] == "alice@example.com"

    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"full_name": "Updated Fictional User"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Fictional User"


def test_password_change_invalidates_old_password(client: TestClient) -> None:
    result = register(client, "alice@example.com", "Fictional Alpha")
    response = client.post(
        "/api/v1/auth/change-password",
        headers=authorization(result["access_token"]),
        json={
            "current_password": "Correct Horse Battery 42!",
            "new_password": "Another Correct Password 43!",
        },
    )
    assert response.status_code == 204

    old_password = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "Correct Horse Battery 42!"},
    )
    new_password = client.post(
        "/api/v1/auth/login",
        data={"username": "alice@example.com", "password": "Another Correct Password 43!"},
    )
    assert old_password.status_code == 401
    assert new_password.status_code == 200


def test_tenant_isolation_for_contacts_and_deals(client: TestClient) -> None:
    alpha = register(client, "alice@example.com", "Fictional Alpha")
    beta = register(client, "bob@example.com", "Fictional Beta")
    alpha_headers = authorization(alpha["access_token"])
    beta_headers = authorization(beta["access_token"])

    contact = client.post(
        "/api/v1/contacts/",
        headers=alpha_headers,
        json={"first_name": "Fictional", "last_name": "Contact"},
    )
    assert contact.status_code == 201, contact.text
    deal = client.post(
        "/api/v1/deals/",
        headers=alpha_headers,
        json={"name": "Fictional Alpha Deal", "contact_id": contact.json()["id"]},
    )
    assert deal.status_code == 201, deal.text

    assert client.get("/api/v1/contacts/", headers=beta_headers).json() == []
    assert client.get("/api/v1/deals/", headers=beta_headers).json() == []
    assert (
        client.get(
            f"/api/v1/contacts/{contact.json()['id']}",
            headers=beta_headers,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/deals/{deal.json()['id']}",
            headers=beta_headers,
        ).status_code
        == 404
    )
    cross_tenant_deal = client.post(
        "/api/v1/deals/",
        headers=beta_headers,
        json={"name": "Fictional Invalid Link", "contact_id": contact.json()["id"]},
    )
    assert cross_tenant_deal.status_code == 404


def test_role_based_access_control(client: TestClient) -> None:
    admin = register(client, "alice@example.com", "Fictional Alpha")
    created = client.post(
        "/api/v1/auth/users",
        headers=authorization(admin["access_token"]),
        json={
            "full_name": "Fictional Investor",
            "email": "investor@example.com",
            "password": "Correct Horse Battery 42!",
            "role": "investor",
        },
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "investor@example.com", "password": "Correct Horse Battery 42!"},
    )
    assert login.status_code == 200
    headers = authorization(login.json()["access_token"])

    assert client.get("/api/v1/auth/users", headers=headers).status_code == 403
    denied_write = client.post(
        "/api/v1/contacts/",
        headers=headers,
        json={"first_name": "Fictional", "last_name": "Contact"},
    )
    assert denied_write.status_code == 403


def test_client_and_originator_crud_onboarding_and_tenant_isolation(
    client: TestClient, tmp_path
) -> None:
    get_settings().document_storage_dir = tmp_path / "uploads"
    alpha = register(client, "alice@example.com", "Fictional Alpha")
    beta = register(client, "bob@example.com", "Fictional Beta")
    alpha_headers = authorization(alpha["access_token"])
    beta_headers = authorization(beta["access_token"])

    originator_response = client.post(
        "/api/v1/originators/",
        headers=alpha_headers,
        json={
            "full_name": "Fictional Originator",
            "email": "originator@example.com",
            "firm_name": "Example Advisory",
            "sectors": "Technology, Healthcare",
        },
    )
    assert originator_response.status_code == 201, originator_response.text
    originator = originator_response.json()
    assert client.get(
        f"/api/v1/originators/{originator['id']}",
        headers=alpha_headers,
    ).status_code == 200

    client_response = client.post(
        "/api/v1/clients/",
        headers=alpha_headers,
        json={
            "name": "Fictional Client",
            "sector": "Technology",
            "location": "Fictional City",
            "revenue": 1250000,
            "funding_requirement": 500000,
            "assigned_originator_id": originator["id"],
        },
    )
    assert client_response.status_code == 201, client_response.text
    business = client_response.json()
    assert business["onboarding_status"] == "not_started"
    assert client.get(
        f"/api/v1/clients/{business['id']}",
        headers=alpha_headers,
    ).status_code == 200
    assert client.get(
        "/api/v1/clients/?sector=Technology",
        headers=alpha_headers,
    ).json()[0]["id"] == business["id"]
    deal = client.post(
        "/api/v1/deals/",
        headers=alpha_headers,
        json={
            "name": "Fictional Filterable Deal",
            "stage": "initial_screening",
            "client_id": business["id"],
            "originator_id": originator["id"],
        },
    )
    assert deal.status_code == 201, deal.text
    filtered_deals = client.get(
        "/api/v1/deals/?stage=initial_screening&sector=Technology"
        f"&originator_id={originator['id']}",
        headers=alpha_headers,
    )
    assert [item["id"] for item in filtered_deals.json()] == [deal.json()["id"]]
    assert client.get("/api/v1/clients/", headers=beta_headers).json() == []
    assert client.get("/api/v1/originators/", headers=beta_headers).json() == []

    changed = client.patch(
        f"/api/v1/clients/{business['id']}",
        headers=alpha_headers,
        json={"onboarding_status": "in_progress", "status": "prospect"},
    )
    assert changed.status_code == 200
    assert changed.json()["onboarding_status"] == "in_progress"
    assert client.patch(
        f"/api/v1/originators/{originator['id']}",
        headers=alpha_headers,
        json={"status": "inactive"},
    ).json()["status"] == "inactive"

    interaction = client.post(
        f"/api/v1/clients/{business['id']}/interactions",
        headers=alpha_headers,
        json={"interaction_type": "meeting", "summary": "Fictional kickoff"},
    )
    assert interaction.status_code == 201, interaction.text
    assert len(
        client.get(
            f"/api/v1/clients/{business['id']}/interactions",
            headers=alpha_headers,
        ).json()
    ) == 1
    simulated_check = client.post(
        f"/api/v1/clients/{business['id']}/verification-checks",
        headers=alpha_headers,
        json={"check_type": "mca"},
    )
    assert simulated_check.status_code == 201, simulated_check.text
    assert simulated_check.json()["status"] == "simulated"
    assert simulated_check.json()["details"]["external_provider_configured"] is False
    assert client.post(
        f"/api/v1/clients/{business['id']}/verification-checks",
        headers=alpha_headers,
        json={"check_type": "unconfigured_registry"},
    ).status_code == 422

    upload = client.post(
        f"/api/v1/clients/{business['id']}/documents",
        headers=alpha_headers,
        files={
            "file": (
                "fictional-onboarding.txt",
                b"Company: Fictional Sample Co\nSector: Technology\nRevenue: 1200000",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert document["name"] == "fictional-onboarding.txt"
    assert document["extracted_fields"]["company_name"] == "Fictional Sample Co"
    assert document["extracted_fields"]["sector"] == "Technology"
    assert client.get(
        f"/api/v1/clients/{business['id']}/documents",
        headers=alpha_headers,
    ).json()[0]["id"] == document["id"]
    downloaded = client.get(
        f"/api/v1/clients/{business['id']}/documents/{document['id']}/file",
        headers=alpha_headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"Company: Fictional Sample Co")
    assert client.delete(
        f"/api/v1/clients/{business['id']}/documents/{document['id']}",
        headers=alpha_headers,
    ).status_code == 204

    assert client.get(
        f"/api/v1/clients/{business['id']}",
        headers=beta_headers,
    ).status_code == 404
    assert client.patch(
        f"/api/v1/clients/{business['id']}",
        headers=beta_headers,
        json={"name": "Cross-tenant update"},
    ).status_code == 404
    assert client.delete(
        f"/api/v1/clients/{business['id']}",
        headers=alpha_headers,
    ).status_code == 204
    assert client.delete(
        f"/api/v1/originators/{originator['id']}",
        headers=alpha_headers,
    ).status_code == 204


def test_deal_pipeline_lifecycle_activity_documents_and_tenant_isolation(
    client: TestClient, tmp_path
) -> None:
    get_settings().document_storage_dir = tmp_path / "uploads"
    alpha = register(client, "alice@example.com", "Fictional Alpha")
    beta = register(client, "bob@example.com", "Fictional Beta")
    alpha_headers = authorization(alpha["access_token"])
    beta_headers = authorization(beta["access_token"])
    originator_response = client.post(
        "/api/v1/originators/",
        headers=alpha_headers,
        json={"full_name": "Fictional Deal Originator"},
    )
    assert originator_response.status_code == 201, originator_response.text
    originator_id = originator_response.json()["id"]
    reassigned_originator = client.post(
        "/api/v1/originators/",
        headers=alpha_headers,
        json={"full_name": "Fictional Reassigned Originator"},
    )
    assert reassigned_originator.status_code == 201, reassigned_originator.text
    reassigned_originator_id = reassigned_originator.json()["id"]

    created = client.post(
        "/api/v1/deals/",
        headers=alpha_headers,
        json={
            "name": "Fictional Growth Raise",
            "company_name": "Fictional Growth Co",
            "industry": "Software",
            "sector": "Technology",
            "deal_type": "Growth financing",
            "transaction_size": 2_500_000,
            "revenue": 8_000_000,
            "ebitda": 1_200_000,
            "funding_requirement": 1_750_000,
            "target_valuation": 12_000_000,
            "description": "Fictional pipeline lifecycle test.",
            "originator_id": originator_id,
            "stage": "lead_identified",
        },
    )
    assert created.status_code == 201, created.text
    deal = created.json()
    deal_id = deal["id"]
    assert deal["value"] == 2_500_000
    assert deal["transaction_size"] == 2_500_000
    assert client.get(
        f"/api/v1/deals/{deal_id}",
        headers=alpha_headers,
    ).json()["company_name"] == "Fictional Growth Co"

    filtered = client.get(
        "/api/v1/deals/?q=Growth&sector=Technology"
        f"&stage=lead_identified&originator_id={originator_id}",
        headers=alpha_headers,
    )
    assert [item["id"] for item in filtered.json()] == [deal_id]
    assert client.get(
        "/api/v1/deals/?q=not-a-match",
        headers=alpha_headers,
    ).json() == []

    updated = client.patch(
        f"/api/v1/deals/{deal_id}",
        headers=alpha_headers,
        json={
            "stage": "due_diligence",
            "transaction_size": 3_000_000,
            "originator_id": reassigned_originator_id,
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["value"] == 3_000_000
    assert updated.json()["stage"] == "due_diligence"
    assert updated.json()["originator_id"] == reassigned_originator_id
    activity = client.get(
        f"/api/v1/deals/{deal_id}/activity",
        headers=alpha_headers,
    )
    assert activity.status_code == 200, activity.text
    assert {item["action"] for item in activity.json()} >= {
        "deal.created",
        "deal.updated",
    }

    upload = client.post(
        f"/api/v1/deals/{deal_id}/documents",
        headers=alpha_headers,
        files={"file": ("fictional-teaser.txt", b"Fictional deal teaser", "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document = upload.json()
    assert client.get(
        f"/api/v1/deals/{deal_id}/documents",
        headers=alpha_headers,
    ).json()[0]["id"] == document["id"]
    download = client.get(
        f"/api/v1/deals/{deal_id}/documents/{document['id']}/file",
        headers=alpha_headers,
    )
    assert download.status_code == 200
    assert download.content == b"Fictional deal teaser"
    assert client.get(
        f"/api/v1/deals/{deal_id}",
        headers=beta_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/deals/{deal_id}/activity",
        headers=beta_headers,
    ).status_code == 404
    assert client.get(
        f"/api/v1/deals/{deal_id}/documents/{document['id']}/file",
        headers=beta_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/deals/{deal_id}/documents/{document['id']}",
        headers=alpha_headers,
    ).status_code == 204
    assert client.delete(
        f"/api/v1/deals/{deal_id}",
        headers=alpha_headers,
    ).status_code == 204
    assert client.get(
        f"/api/v1/deals/{deal_id}",
        headers=alpha_headers,
    ).status_code == 404
    assert client.post(
        "/api/v1/deals/",
        headers=alpha_headers,
        json={"name": "Fictional Invalid Stage", "stage": "qualification"},
    ).status_code == 422


def _force_mock_mode(monkeypatch) -> None:
    monkeypatch.setenv("AI_MOCK_MODE", "true")
    for name in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "AZURE_API_KEY",
        "COHERE_API_KEY",
        "MISTRAL_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def test_mandate_generation_docx_workflow_requires_approval_and_is_tenant_scoped(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    _force_mock_mode(monkeypatch)
    get_settings().document_storage_dir = tmp_path / "uploads"
    alpha = register(client, "alice@example.com", "Fictional Alpha")
    beta = register(client, "bob@example.com", "Fictional Beta")
    alpha_headers = authorization(alpha["access_token"])
    beta_headers = authorization(beta["access_token"])
    source = _sample_docx(
        [
            "Company Name: Fictional Robotics Co",
            "Industry: Industrial automation",
            "Sector: Industrials",
            "Revenue: USD 12,500,000",
            "EBITDA: USD 2,100,000",
            "Liabilities: USD 4,000,000",
            "Assets: USD 11,000,000",
            "Funding Requirement: USD 5,000,000",
        ]
    )
    uploaded = client.post(
        "/api/v1/mandate-generations/",
        headers=alpha_headers,
        files={"file": ("fictional-robotics.docx", source, "application/docx")},
    )
    assert uploaded.status_code == 201, uploaded.text
    generation_id = uploaded.json()["id"]
    assert uploaded.json()["status"] == "uploaded"
    assert uploaded.json()["source_document_name"] == "fictional-robotics.docx"

    processed = client.post(
        f"/api/v1/mandate-generations/{generation_id}/process",
        headers=alpha_headers,
    )
    assert processed.status_code == 200, processed.text
    result = processed.json()
    assert result["status"] == "awaiting_review"
    assert result["processing_mode"] == "mock"
    assert result["extracted_data"]["document_type"] == "docx"
    assert result["financial_analysis"]["revenue"]["value"] == "USD 12,500,000"
    assert (
        result["financial_analysis"]["revenue"]["source"]["quote"]
        == "Revenue: USD 12,500,000"
    )
    assert result["financial_analysis"]["revenue"]["source"]["location"] == "paragraph 4"
    assert result["financial_analysis"]["profitability"]["status"] == "unavailable"
    assert "Fictional Robotics Co" not in result["teaser_draft"]
    assert "fictional-robotics.docx" not in result["teaser_draft"]
    assert "[Source:" not in result["teaser_draft"]
    assert len(result["agent_history"]) == 7

    downloaded = client.get(
        f"/api/v1/mandate-generations/{generation_id}/source",
        headers=alpha_headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content == source
    assert client.get(
        f"/api/v1/mandate-generations/{generation_id}",
        headers=beta_headers,
    ).status_code == 404
    assert client.get(
        "/api/v1/mandate-generations/",
        headers=beta_headers,
    ).json() == []

    edited = client.patch(
        f"/api/v1/mandate-generations/{generation_id}",
        headers=alpha_headers,
        json={
            "mandate_draft": result["mandate_draft"] + "\nReviewer edit.",
            "teaser_draft": result["teaser_draft"] + "\nReviewer edit.",
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["mandate_draft"].endswith("Reviewer edit.")
    approved = client.post(
        f"/api/v1/mandate-generations/{generation_id}/approve",
        headers=alpha_headers,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_by_id"] == alpha["user"]["id"]
    assert client.patch(
        f"/api/v1/mandate-generations/{generation_id}",
        headers=alpha_headers,
        json={"mandate_draft": "Changed after approval"},
    ).status_code == 409


def test_mandate_generation_pdf_retains_citations_and_unavailable_values(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    _force_mock_mode(monkeypatch)
    get_settings().document_storage_dir = tmp_path / "uploads"
    account = register(client, "alice@example.com", "Fictional Alpha")
    headers = authorization(account["access_token"])
    source = _sample_pdf(
        [
            "Company Name: Fictional Components Ltd",
            "Revenue: USD 8,750,000",
        ]
    )
    uploaded = client.post(
        "/api/v1/mandate-generations/",
        headers=headers,
        files={"file": ("fictional-components.pdf", source, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    generation_id = uploaded.json()["id"]
    processed = client.post(
        f"/api/v1/mandate-generations/{generation_id}/process",
        headers=headers,
    )
    assert processed.status_code == 200, processed.text
    result = processed.json()
    assert result["extracted_data"]["document_type"] == "pdf"
    revenue = result["financial_analysis"]["revenue"]
    assert revenue["value"] == "USD 8,750,000"
    assert revenue["source"]["location"] == "page 1"
    assert revenue["source"]["quote"] == "Revenue: USD 8,750,000"
    assert result["financial_analysis"]["ebitda"]["value"] is None
    assert result["financial_analysis"]["ebitda"]["status"] == "unavailable"
    assert "ebitda" in result["quality_review"]["missing_fields"]
    assert "Unavailable" in result["mandate_draft"]


def test_mandate_generation_llm_facts_are_source_checked_before_approval(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("AI_MOCK_MODE", "false")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    get_settings().document_storage_dir = tmp_path / "uploads"

    async def fake_chat(self, messages, **kwargs):
        assert self.temperature == 0
        assert "Revenue: USD 8,750,000" in messages[-1]["content"]
        assert kwargs["response_format"] == {"type": "json_object"}
        return (
            '{"facts": {'
            '"company_name": {"value": "Fictional Components Ltd", '
            '"quote": "Company Name: Fictional Components Ltd", '
            '"location": "page 999"}, '
            '"revenue": {"value": "USD 99,000,000", '
            '"quote": "Revenue: USD 8,750,000", "location": "page 999"}'
            '}}'
        )

    monkeypatch.setattr(LLMClient, "chat", fake_chat)
    account = register(client, "alice@example.com", "Fictional Alpha")
    headers = authorization(account["access_token"])
    source = _sample_pdf(
        [
            "Company Name: Fictional Components Ltd",
            "Revenue: USD 8,750,000",
        ]
    )
    uploaded = client.post(
        "/api/v1/mandate-generations/",
        headers=headers,
        files={"file": ("fictional-components.pdf", source, "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    generation_id = uploaded.json()["id"]

    processed = client.post(
        f"/api/v1/mandate-generations/{generation_id}/process",
        headers=headers,
    )
    assert processed.status_code == 200, processed.text
    result = processed.json()
    assert result["processing_mode"] == "litellm"
    assert result["deal_proposal"]["company_name"]["source"]["location"] == "page 1"
    revenue = result["financial_analysis"]["revenue"]
    assert revenue["source"]["quote"] == "Revenue: USD 8,750,000"
    assert revenue["source"]["location"] == "page 1"
    assert "revenue" in result["quality_review"]["unsupported_claims"]
    assert client.post(
        f"/api/v1/mandate-generations/{generation_id}/approve",
        headers=headers,
    ).status_code == 409


def test_mandate_generation_invalid_document_is_reported_as_failed(
    client: TestClient, tmp_path, monkeypatch
) -> None:
    _force_mock_mode(monkeypatch)
    get_settings().document_storage_dir = tmp_path / "uploads"
    account = register(client, "alice@example.com", "Fictional Alpha")
    headers = authorization(account["access_token"])
    uploaded = client.post(
        "/api/v1/mandate-generations/",
        headers=headers,
        files={"file": ("broken.pdf", b"not a PDF", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    generation_id = uploaded.json()["id"]
    failed = client.post(
        f"/api/v1/mandate-generations/{generation_id}/process",
        headers=headers,
    )
    assert failed.status_code == 422
    record = client.get(
        f"/api/v1/mandate-generations/{generation_id}",
        headers=headers,
    )
    assert record.json()["status"] == "failed"
    assert "PDF file could not be read" in record.json()["error_message"]
