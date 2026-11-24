"""
DealForge shared constants.
Imported by both the backend and agents modules.
"""

# API versioning
API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"

# Deal pipeline stages
class DealStage:
    LEAD_IDENTIFIED = "lead_identified"
    INITIAL_SCREENING = "initial_screening"
    CLIENT_ONBOARDING = "client_onboarding"
    MANDATE_DRAFTING = "mandate_drafting"
    DUE_DILIGENCE = "due_diligence"
    INVESTOR_MATCHING = "investor_matching"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"

    ALL = [
        LEAD_IDENTIFIED,
        INITIAL_SCREENING,
        CLIENT_ONBOARDING,
        MANDATE_DRAFTING,
        DUE_DILIGENCE,
        INVESTOR_MATCHING,
        NEGOTIATION,
        CLOSED_WON,
        CLOSED_LOST,
    ]

# Contact types
class ContactType:
    LEAD = "lead"
    PROSPECT = "prospect"
    CUSTOMER = "customer"
    PARTNER = "partner"

    ALL = [LEAD, PROSPECT, CUSTOMER, PARTNER]

# Default pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
