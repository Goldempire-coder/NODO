"use client";

import { useCallback, useRef, useState } from "react";
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
  pushBackView,
  request,
  setBusy,
  setNotice,
  setView
}: {
  handlers: InvestigationHandlers;
  pushBackView: (view: AdminWebView) => void;
  request: RequestFn;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
}) {
  const [investigationQuery, setInvestigationQuery] = useState("");
  const [investigationResults, setInvestigationResults] = useState<AdminInvestigationSearchResponse>(EMPTY_SEARCH);
  const [investigationSearched, setInvestigationSearched] = useState(false);
  const lastInvestigationQuery = useRef("");

  const setInvestigationQueryValue = useCallback((value: string) => {
    setInvestigationQuery(value);
    if (investigationSearched && value.trim() !== lastInvestigationQuery.current) {
      setInvestigationResults(EMPTY_SEARCH);
      setInvestigationSearched(false);
    }
  }, [investigationSearched]);

  const clearInvestigationSearch = useCallback(() => {
    lastInvestigationQuery.current = "";
    setInvestigationQuery("");
    setInvestigationResults(EMPTY_SEARCH);
    setInvestigationSearched(false);
    setView("investigation");
    setNotice("Busqueda limpia.");
  }, [setNotice, setView]);

  const searchInvestigation = useCallback(async (query = investigationQuery) => {
    const normalizedQuery = query.trim();
    setInvestigationQuery(query);
    setView("investigation");
    if (normalizedQuery.length < 3) {
      lastInvestigationQuery.current = "";
      setInvestigationResults(EMPTY_SEARCH);
      setInvestigationSearched(false);
      setNotice("Escribe al menos 3 caracteres para buscar.");
      return;
    }
    setBusy(true);
    try {
      const data = await searchAdminInvestigation<AdminInvestigationSearchResponse>(request, normalizedQuery);
      lastInvestigationQuery.current = normalizedQuery;
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
    pushBackView("investigation");
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
  }, [handlers, pushBackView]);

  const openInvestigationCaseFile = useCallback(async (item: AdminInvestigationSearchItem) => {
    pushBackView("investigation");
    await handlers.openCaseFile(item);
  }, [handlers, pushBackView]);

  return {
    investigationQuery,
    setInvestigationQuery: setInvestigationQueryValue,
    investigationResults,
    investigationSearched,
    clearInvestigationSearch,
    searchInvestigation,
    openInvestigationResult,
    openInvestigationCaseFile
  };
}
