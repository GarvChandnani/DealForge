/**
 * DealForge Frontend — Axios API Client.
 *
 * Singleton Axios instance with:
 * - Base URL from VITE_API_URL env var.
 * - Request/response interceptors for auth and error normalization.
 * - Typed helper methods for all API resources.
 */

import axios from "axios";
import type { AxiosInstance, AxiosResponse } from "axios";
import type {
  AuthResponse, AuthUser, Deal, Contact, HealthResponse, Client, Originator,
  ClientDocument, ClientInteraction, DealActivity, DealDocument,
  VerificationCheck,
  Mandate, MandateGeneration,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const client: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 15_000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// ── Request interceptor — attach auth token when available ────────────────────
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("dealforge_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor — normalize errors ───────────────────────────────────
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const problemDetail = error.response?.data;
    // Enrich the error so callers can display problem detail directly
    if (problemDetail?.title) {
      error.message = `${problemDetail.title}: ${problemDetail.detail}`;
    }
    return Promise.reject(error);
  }
);

// ── Typed API helpers ─────────────────────────────────────────────────────────

export const healthApi = {
  get: (): Promise<AxiosResponse<HealthResponse>> =>
    client.get<HealthResponse>("/health"),
};

export const authApi = {
  login: (email: string, password: string) =>
    client.post<AuthResponse>(
      "/auth/login",
      new URLSearchParams({ username: email, password }),
      { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
    ),
  register: (payload: {
    organization_name: string;
    full_name: string;
    email: string;
    password: string;
  }) => client.post<AuthResponse>("/auth/register", payload),
  me: () => client.get<AuthUser>("/auth/me"),
};

export const dealsApi = {
  list: (params?: { skip?: number; limit?: number; stage?: string; sector?: string; originator_id?: string; q?: string }) =>
    client.get<Deal[]>("/deals/", { params }),
  get: (id: string) => client.get<Deal>(`/deals/${id}`),
  create: (payload: Partial<Deal>) => client.post<Deal>("/deals/", payload),
  update: (id: string, payload: Partial<Deal>) =>
    client.patch<Deal>(`/deals/${id}`, payload),
  delete: (id: string) => client.delete(`/deals/${id}`),
  activity: (id: string) => client.get<DealActivity[]>(`/deals/${id}/activity`),
  documents: (id: string) => client.get<DealDocument[]>(`/deals/${id}/documents`),
  uploadDocument: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return client.post<DealDocument>(`/deals/${id}/documents`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deleteDocument: (dealId: string, documentId: string) =>
    client.delete(`/deals/${dealId}/documents/${documentId}`),
  downloadDocument: (dealId: string, documentId: string) =>
    client.get<Blob>(`/deals/${dealId}/documents/${documentId}/file`, {
      responseType: "blob",
    }),
};

export const contactsApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    client.get<Contact[]>("/contacts/", { params }),
  get: (id: string) => client.get<Contact>(`/contacts/${id}`),
  create: (payload: Partial<Contact>) =>
    client.post<Contact>("/contacts/", payload),
  update: (id: string, payload: Partial<Contact>) =>
    client.patch<Contact>(`/contacts/${id}`, payload),
  delete: (id: string) => client.delete(`/contacts/${id}`),
};

export const originatorsApi = {
  list: (params?: { skip?: number; limit?: number }) =>
    client.get<Originator[]>("/originators/", { params }),
  get: (id: string) => client.get<Originator>(`/originators/${id}`),
  create: (payload: Partial<Originator>) =>
    client.post<Originator>("/originators/", payload),
  update: (id: string, payload: Partial<Originator>) =>
    client.patch<Originator>(`/originators/${id}`, payload),
  delete: (id: string) => client.delete(`/originators/${id}`),
};

export const mandatesApi = {
  list: (params?: { originator_id?: string }) =>
    client.get<Mandate[]>("/mandates/", { params }),
};

export const mandateGenerationsApi = {
  list: () => client.get<MandateGeneration[]>("/mandate-generations/"),
  get: (id: string) => client.get<MandateGeneration>(`/mandate-generations/${id}`),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return client.post<MandateGeneration>("/mandate-generations/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  process: (id: string) =>
    client.post<MandateGeneration>(`/mandate-generations/${id}/process`, undefined, {
      timeout: 120_000,
    }),
  update: (id: string, payload: { mandate_draft?: string; teaser_draft?: string }) =>
    client.patch<MandateGeneration>(`/mandate-generations/${id}`, payload),
  approve: (id: string) =>
    client.post<MandateGeneration>(`/mandate-generations/${id}/approve`),
  downloadSource: (id: string) =>
    client.get<Blob>(`/mandate-generations/${id}/source`, { responseType: "blob" }),
};

export const clientsApi = {
  list: (params?: {
    skip?: number; limit?: number; status_filter?: string; sector?: string; originator_id?: string;
  }) => client.get<Client[]>("/clients/", { params }),
  get: (id: string) => client.get<Client>(`/clients/${id}`),
  create: (payload: Partial<Client>) => client.post<Client>("/clients/", payload),
  update: (id: string, payload: Partial<Client>) =>
    client.patch<Client>(`/clients/${id}`, payload),
  delete: (id: string) => client.delete(`/clients/${id}`),
  interactions: (id: string) =>
    client.get<ClientInteraction[]>(`/clients/${id}/interactions`),
  addInteraction: (id: string, payload: Pick<ClientInteraction, "interaction_type" | "summary" | "notes">) =>
    client.post<ClientInteraction>(`/clients/${id}/interactions`, payload),
  documents: (id: string) => client.get<ClientDocument[]>(`/clients/${id}/documents`),
  uploadDocument: (id: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return client.post<ClientDocument>(`/clients/${id}/documents`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  deleteDocument: (clientId: string, documentId: string) =>
    client.delete(`/clients/${clientId}/documents/${documentId}`),
  downloadDocument: (clientId: string, documentId: string) =>
    client.get<Blob>(`/clients/${clientId}/documents/${documentId}/file`, {
      responseType: "blob",
    }),
  verificationChecks: (id: string) =>
    client.get<VerificationCheck[]>(`/clients/${id}/verification-checks`),
  runSimulatedCheck: (id: string, check_type: string) =>
    client.post<VerificationCheck>(`/clients/${id}/verification-checks`, { check_type }),
};

export default client;
