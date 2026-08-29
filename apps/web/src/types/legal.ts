export type BusinessLegalDocumentSet = "business_terms" | "business_credit_terms";

export type BusinessLegalRequirement = {
  document_set: BusinessLegalDocumentSet;
  document_version: string;
  title: string;
  accepted: boolean;
  accepted_at: string | null;
};

export type BusinessLegalRequirements = {
  business_id: string;
  requirements: BusinessLegalRequirement[];
};

export type BusinessLegalAcceptanceResponse = {
  acceptance: {
    id: string;
    business_id: string;
    user_id: string;
    document_set: BusinessLegalDocumentSet;
    document_version: string;
    accepted_at: string;
  };
  requirements: BusinessLegalRequirement[];
};
