"""Idempotently create fictional DealForge demonstration records.

Usage from the repository root:
    $env:DEALFORGE_DEMO_PASSWORD = "<your local demo password>"
    python database/seeds/seed_data.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

REPOSITORY_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPOSITORY_DIR / "backend"
sys.path.insert(0, str(REPOSITORY_DIR))
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPOSITORY_DIR / ".env")

from app.config import get_settings
from app.db.session import AsyncSessionLocal, create_all_tables
from app.models import (
    ActivityLog,
    Client,
    ComplianceRecord,
    Contact,
    Deal,
    DealMatch,
    Document,
    Investor,
    Mandate,
    Organization,
    Originator,
    Transaction,
    User,
    UserRole,
)
from app.security import hash_password

DEMO_ORGANIZATION = "Fictional DealForge Demo Workspace"
DEMO_SLUG = "fictional-dealforge-demo"
DEMO_ADMIN_EMAIL = "demo-admin@example.com"


async def get_or_create(session, model, **values):
    result = await session.execute(
        select(model).where(*(getattr(model, key) == value for key, value in values.items()))
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        instance = model(**values)
        session.add(instance)
        await session.flush()
    return instance


async def seed() -> None:
    password = os.getenv("DEALFORGE_DEMO_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "Set DEALFORGE_DEMO_PASSWORD before seeding; no demo password is hardcoded."
        )

    await create_all_tables()
    async with AsyncSessionLocal() as session:
        organization = await get_or_create(
            session,
            Organization,
            slug=DEMO_SLUG,
            name=DEMO_ORGANIZATION,
            is_demo=True,
        )
        admin_result = await session.execute(
            select(User).where(
                User.organization_id == organization.id,
                User.email == DEMO_ADMIN_EMAIL,
            )
        )
        admin = admin_result.scalar_one_or_none()
        if admin is None:
            admin = User(
                organization_id=organization.id,
                email=DEMO_ADMIN_EMAIL,
                full_name="Fictional Demo Administrator",
                password_hash=hash_password(password),
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            session.add(admin)
            await session.flush()
        originator = await get_or_create(
            session,
            Originator,
            organization_id=organization.id,
            user_id=admin.id,
            firm_name="Fictional DealForge Advisory",
            biography="Fictional sample originator for local demonstrations.",
        )
        originator.full_name = admin.full_name
        originator.email = admin.email
        originator.title = "Fictional Managing Director"
        originator.sectors = "Industrial automation, healthcare technology"
        originator.status = "active"
        partner_originator = await get_or_create(
            session,
            Originator,
            organization_id=organization.id,
            user_id=None,
            firm_name="Fictional Meridian Advisory",
            full_name="Taylor Example",
            email="taylor@meridian.example.com",
            biography="Fictional originator profile for local demonstrations.",
            sectors="Healthcare technology, enterprise software",
            status="active",
        )

        clients = [
            await get_or_create(
                session,
                Client,
                organization_id=organization.id,
                name="Example Robotics (Fictional)",
                industry="Industrial automation",
                website="https://robotics.example.com",
                contact_email="operations@robotics.example.com",
                description="Fictional client record for local demonstrations.",
            ),
            await get_or_create(
                session,
                Client,
                organization_id=organization.id,
                name="Example Health Systems (Fictional)",
                industry="Healthcare technology",
                website="https://health.example.com",
                contact_email="team@health.example.com",
                description="Fictional client record for local demonstrations.",
            ),
        ]
        for client, sector, location, turnover, revenue, funding, assigned_originator in (
            (clients[0], "Industrial automation", "Fictional City A", "4200000", "3100000", "2500000", originator),
            (clients[1], "Healthcare technology", "Fictional City B", "7800000", "5600000", "4000000", partner_originator),
        ):
            client.sector = sector
            client.location = location
            client.turnover = turnover
            client.revenue = revenue
            client.funding_requirement = funding
            client.assigned_originator_id = assigned_originator.id
            client.currency = "USD"
            client.onboarding_status = "in_progress"
        contacts = [
            await get_or_create(
                session,
                Contact,
                organization_id=organization.id,
                first_name="Riley",
                last_name="Hart",
                email="riley.hart@robotics.example.com",
                company=clients[0].name,
                title="Fictional Chief Executive",
                contact_type="prospect",
                notes="Fictional demonstration contact.",
            ),
            await get_or_create(
                session,
                Contact,
                organization_id=organization.id,
                first_name="Morgan",
                last_name="Blake",
                email="morgan.blake@health.example.com",
                company=clients[1].name,
                title="Fictional Finance Lead",
                contact_type="lead",
                notes="Fictional demonstration contact.",
            ),
        ]
        investors = [
            await get_or_create(
                session,
                Investor,
                organization_id=organization.id,
                name="Example Growth Fund (Fictional)",
                investor_type="institutional",
                contact_email="investments@growth.example.com",
                preferred_sectors="industrial automation, healthcare technology",
            ),
            await get_or_create(
                session,
                Investor,
                organization_id=organization.id,
                name="Example Ventures (Fictional)",
                investor_type="venture_capital",
                contact_email="team@ventures.example.com",
                preferred_sectors="enterprise software",
            ),
        ]
        deal_specs = [
            ("Fictional Robotics Growth Advisory", "Fictional Robotics Co", "Industrials", "lead_identified", 2_500_000, clients[0], contacts[0], 10),
            ("Fictional Health Systems Partnership", "Fictional Health Systems", "Healthcare", "initial_screening", 850_000, clients[1], contacts[1], 25),
            ("Fictional Cloud Services Financing", "Fictional Cloud Services", "Technology", "client_onboarding", 1_200_000, clients[0], contacts[0], 35),
            ("Fictional Consumer Brands Mandate", "Fictional Consumer Brands", "Consumer", "mandate_drafting", 3_400_000, clients[1], contacts[1], 45),
            ("Fictional Precision Components Review", "Fictional Precision Components", "Industrials", "due_diligence", 4_100_000, clients[0], contacts[0], 60),
            ("Fictional Digital Health Placement", "Fictional Digital Health", "Healthcare", "investor_matching", 1_750_000, clients[1], contacts[1], 70),
            ("Fictional Logistics Negotiation", "Fictional Logistics", "Business Services", "negotiation", 5_000_000, clients[0], contacts[0], 85),
            ("Fictional Analytics Closed Won", "Fictional Analytics", "Technology", "closed_won", 2_100_000, clients[1], contacts[1], 100),
            ("Fictional Retail Closed Lost", "Fictional Retail Group", "Consumer", "closed_lost", 900_000, clients[0], contacts[0], 0),
        ]
        deals = []
        for name, company_name, sector, stage, amount, client, contact, probability in deal_specs:
            deal = await get_or_create(
                session,
                Deal,
                organization_id=organization.id,
                name=name,
            )
            deal.stage = stage
            deal.value = amount
            deal.transaction_size = amount
            deal.currency = "USD"
            deal.company_name = company_name
            deal.industry = sector
            deal.sector = sector
            deal.deal_type = "Growth financing"
            deal.revenue = amount * 3
            deal.ebitda = amount // 5
            deal.funding_requirement = amount
            deal.target_valuation = amount * 4
            deal.probability = probability
            deal.description = "Fictional example deal; not a real opportunity."
            deal.contact_id = contact.id
            deal.client_id = client.id
            deal.originator_id = originator.id
            deal.created_by_id = admin.id
            deals.append(deal)
            await get_or_create(
                session,
                ActivityLog,
                organization_id=organization.id,
                actor_user_id=admin.id,
                action="deal.created",
                entity_type="deal",
                entity_id=deal.id,
            )

        await get_or_create(
            session,
            DealMatch,
            organization_id=organization.id,
            deal_id=deals[0].id,
            investor_id=investors[0].id,
            match_score="87.50",
            status="suggested",
            notes="Fictional example investor match.",
        )
        await get_or_create(
            session,
            Mandate,
            organization_id=organization.id,
            name="Fictional Robotics Capital Raise",
            client_id=clients[0].id,
            originator_id=originator.id,
            description="Fictional mandate for demonstrating the schema.",
            target_value="2500000.00",
        )
        document_name = "Fictional information memorandum.txt"
        document_key = "fictional-demo/robotics/information-memorandum.txt"
        document_result = await session.execute(
            select(Document).where(
                Document.organization_id == organization.id,
                Document.deal_id == deals[0].id,
                Document.name.in_(
                    ["Fictional information memorandum", document_name]
                ),
            )
        )
        sample_document = document_result.scalar_one_or_none()
        if sample_document is None:
            sample_document = Document(
                organization_id=organization.id,
                deal_id=deals[0].id,
                client_id=clients[0].id,
                uploaded_by_id=admin.id,
                name=document_name,
                storage_key=document_key,
                content_type="text/plain",
                size_bytes=0,
            )
            session.add(sample_document)
        else:
            sample_document.name = document_name
            sample_document.storage_key = document_key
            sample_document.content_type = "text/plain"
        sample_content = (
            "FICTIONAL DEMONSTRATION DOCUMENT\n"
            "Company: Fictional Robotics Co\n"
            "This sample file is not a real client or transaction document.\n"
        ).encode("utf-8")
        sample_document.size_bytes = len(sample_content)
        document_path = get_settings().document_storage_dir / document_key
        document_path.parent.mkdir(parents=True, exist_ok=True)
        document_path.write_bytes(sample_content)
        await get_or_create(
            session,
            ActivityLog,
            organization_id=organization.id,
            actor_user_id=admin.id,
            action="deal.document_uploaded",
            entity_type="deal",
            entity_id=deals[0].id,
        )
        await get_or_create(
            session,
            ComplianceRecord,
            organization_id=organization.id,
            entity_type="client",
            entity_id=clients[0].id,
            check_type="fictional_sample_review",
            status="pending",
            details={"fictional": True, "note": "Demonstration data only."},
        )
        await get_or_create(
            session,
            Transaction,
            organization_id=organization.id,
            deal_id=deals[0].id,
            client_id=clients[0].id,
            amount="25000.00",
            currency="USD",
            status="pending",
            reference="FICTIONAL-DEMO-001",
        )
        await get_or_create(
            session,
            ActivityLog,
            organization_id=organization.id,
            actor_user_id=admin.id,
            action="demo.seeded",
            entity_type="organization",
            entity_id=organization.id,
            details={"fictional": True},
        )
        await session.commit()

    print(
        "Seeded idempotent fictional DealForge demo data. "
        "Demo administrator: demo-admin@example.com"
    )


if __name__ == "__main__":
    asyncio.run(seed())
