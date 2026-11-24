/**
 * DealForge Frontend — Global TypeScript Types.
 */

// ── API response types ────────────────────────────────────────────────────────

export interface HealthDependency {
  status: "ok" | "error";
  driver?: string;
  error?: string;
}

export interface HealthResponse {
  status: "ok" | "degraded" | "error";
  version: string;
  environment: string;
  uptime_seconds: number;
  dependencies: {
    database: HealthDependency;
  };
}

export type UserRole = "admin" | "originator" | "analyst" | "investor";

export interface AuthUser {
  id: string;
  organization_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
  organization: {
    id: string;
    name: string;
    slug: string;
    is_demo: boolean;
  };
}

// ── CRM types ─────────────────────────────────────────────────────────────────

export type DealStage =
  | "lead_identified"
  | "initial_screening"
  | "client_onboarding"
  | "mandate_drafting"
  | "due_diligence"
  | "investor_matching"
  | "negotiation"
  | "closed_won"
  | "closed_lost";

export type ContactType = "lead" | "prospect" | "customer" | "partner";

export interface Deal {
  id: string;
  name: string;
  company_name?: string | null;
  industry?: string | null;
  sector?: string | null;
  deal_type?: string | null;
  transaction_size?: number | null;
  revenue?: number | null;
  ebitda?: number | null;
  funding_requirement?: number | null;
  target_valuation?: number | null;
  stage: DealStage;
  value?: number | null;
  currency: string;
  probability?: number | null;
  description?: string | null;
  contact_id?: string | null;
  client_id?: string | null;
  originator_id?: string | null;
  ai_summary?: string | null;
  ai_next_action?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DealDocument {
  id: string;
  name: string;
  content_type?: string | null;
  size_bytes?: number | null;
  deal_id?: string | null;
  created_at: string;
}

export interface DealActivity {
  id: string;
  actor_user_id?: string | null;
  action: string;
  entity_type: string;
  entity_id?: string | null;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export interface Contact {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  title?: string | null;
  contact_type: ContactType;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface Originator {
  id: string;
  user_id?: string | null;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  title?: string | null;
  firm_name?: string | null;
  biography?: string | null;
  sectors?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Client {
  id: string;
  name: string;
  industry?: string | null;
  sector?: string | null;
  website?: string | null;
  contact_email?: string | null;
  phone?: string | null;
  location?: string | null;
  turnover?: number | null;
  revenue?: number | null;
  funding_requirement?: number | null;
  currency: string;
  assigned_originator_id?: string | null;
  description?: string | null;
  status: string;
  onboarding_status: string;
  created_at: string;
  updated_at: string;
}

export interface ClientInteraction {
  id: string;
  client_id: string;
  user_id?: string | null;
  interaction_type: string;
  summary: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClientDocument {
  id: string;
  name: string;
  content_type?: string | null;
  size_bytes?: number | null;
  client_id?: string | null;
  extracted_fields?: Record<string, string> | null;
  created_at: string;
}

export interface VerificationCheck {
  id: string;
  entity_type: string;
  entity_id: string;
  check_type: string;
  status: string;
  details?: Record<string, unknown> | null;
  created_at: string;
}

export interface Mandate {
  id: string;
  name: string;
  client_id: string;
  originator_id?: string | null;
  description?: string | null;
  target_value?: number | null;
  currency: string;
  status: string;
  expires_on?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SourceReference {
  document_id: string;
  file_name: string;
  location: string;
  quote: string;
}

export interface FieldEvidence {
  value: string | null;
  status: "available" | "unavailable";
  source: SourceReference | null;
}

export interface MandateGeneration {
  id: string;
  source_document_id: string;
  source_document_name: string;
  status: "uploaded" | "processing" | "awaiting_review" | "approved" | "failed";
  processing_mode: "mock" | "litellm" | null;
  extracted_data: {
    facts: Record<string, FieldEvidence>;
    conflicts: Array<{ field: string; values: string[]; sources: SourceReference[] }>;
  } | null;
  financial_analysis: Record<string, FieldEvidence> | null;
  deal_proposal: {
    title: string;
    source_document_id: string;
    [key: string]: FieldEvidence | string;
  } | null;
  mandate_draft: string | null;
  teaser_draft: string | null;
  quality_review: {
    missing_fields: string[];
    contradictions: string[];
    unsupported_claims: string[];
    passed: boolean;
  } | null;
  agent_history: Array<{
    agent: string;
    status: string;
    summary?: string;
    message?: string;
    mode?: string;
    completed_at?: string;
    started_at?: string;
    approved_at?: string;
  }>;
  error_message: string | null;
  approved_by_id: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

// ── Error types ───────────────────────────────────────────────────────────────

export interface ProblemDetail {
  status: number;
  title: string;
  detail: string;
  instance?: string;
}
