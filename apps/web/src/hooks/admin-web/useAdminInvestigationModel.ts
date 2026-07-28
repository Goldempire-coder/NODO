"use client";

import { useCallback, useState } from "react";
import { searchAdminInvestigation } from "../../api/admin";
import type { AdminInvestigationSearchItem, AdminInvestigationSearchResponse } from "../../types/admin";
import type { AdminWebView, RequestFn } from "./adminWebTypes";

const EMPTY_SEARCH: AdminInvestigationSearchResponse = {
  groups: {
    users: [],
    businesses: [],
    business_intakes: [],
    orders: [],
    support_tickets: []
  },
  result_counts: {},
  disclaimer: ""
};

type InvestigationHandlers = {
  openUser: (id: string) => Promise<void>;
  openBusiness: (id: string) => Promise<void>;
  openBusinessIntake: (id: string) => Promise<void>;
  openOrder: (id: string) => Promise<void>;
  openSupportTicket: (id: string) => Promise<void>;
  openCaseFile: (item: AdminInvestigationSearchItem) => Promise<void>;
};

export function useAdminInvestigationModel({
  handlers,
  request,
  setBusy,
  setNotice,
  setView
}: {
  handlers: InvestigationHandlers;
  request: RequestFn;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
}) {
  const [investigationQuery, setInvestigationQuery] = useState("");
  const [investigationResults, setInvestigationResults] = useState<AdminInvestigationSearchResponse>(EMPTY_SEARCH);
  const [investigationSearched, setInvestigationSearched] = useState(false);

  const searchInvestigation = useCallback(async (query = investigationQuery) => {
    const normalizedQuery = query.trim();
    setInvestigationQuery(query);
    setView("investigation");
    if (normalizedQuery.length < 3) {
      setInvestigationSearched(false);
      setNotice("Escribe al menos 3 caracteres para buscar.");
      return;
    }
    setBusy(true);
    try {
      const data = await searchAdminInvestigation<AdminInvestigationSearchResponse>(request, normalizedQuery);
      setInvestigationResults(data);
      setInvestigationSearched(true);
      const total = Object.values(data.result_counts).reduce((sum, value) => sum + value, 0);
      setNotice(total ? `Encontramos ${total} resultado(s) relacionado(s).` : "No encontramos resultados con esa pista.");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos completar la busqueda.");
    } finally {
      setBusy(false);
    }
  }, [investigationQuery, request, setBusy, setNotice, setView]);

  const openInvestigationResult = useCallback(async (item: AdminInvestigationSearchItem) => {
    if (item.type === "user") {
      await handlers.openUser(item.id);
      return;
    }
    if (item.type === "business") {
      await handlers.openBusiness(item.id);
      return;
    }
    if (item.type === "business_intake") {
      await handlers.openBusinessIntake(item.id);
      return;
    }
    if (item.type === "order") {
      await handlers.openOrder(item.id);
      return;
    }
    if (item.type === "support_ticket") {
      await handlers.openSupportTicket(item.id);
    }
  }, [handlers]);

  return {
    investigationQuery,
    setInvestigationQuery,
    investigationResults,
    investigationSearched,
    searchInvestigation,
    openInvestigationResult,
    openInvestigationCaseFile: handlers.openCaseFile
  };
}
