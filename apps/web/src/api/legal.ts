import type { AuthenticatedRequest } from "./client";
import type {
  BusinessLegalAcceptanceResponse,
  BusinessLegalDocumentSet,
  BusinessLegalRequirements,
} from "../types/legal";

export const BUSINESS_LEGAL_CONFIRMATION = "ACCEPTED_BY_AUTHORIZED_BUSINESS_REPRESENTATIVE";
export const BUSINESS_TERMS_DOCUMENT_SET = "business_terms";
export const BUSINESS_CREDIT_TERMS_DOCUMENT_SET = "business_credit_terms";

export function getBusinessLegalRequirements(request: AuthenticatedRequest) {
  return request<BusinessLegalRequirements>("/api/v1/business/legal/requirements", {
    cache: "no-store",
  });
}

export function acceptBusinessLegalTerms(
  request: AuthenticatedRequest,
  documentSet: BusinessLegalDocumentSet,
  documentVersion: string,
) {
  return request<BusinessLegalAcceptanceResponse>("/api/v1/business/legal/acceptances", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_set: documentSet,
      document_version: documentVersion,
      confirmation: BUSINESS_LEGAL_CONFIRMATION,
    }),
  });
}
