"use client";

import { useCallback, useRef, useState } from "react";
import { searchAdminInvestigationCandidates } from "../../api/admin";
import type {
  AdminInvestigationCandidate,
  AdminInvestigationCandidateFilters,
  AdminInvestigationCandidatesResponse
} from "../../types/admin";
import type { AdminWebView, RequestFn } from "./adminWebTypes";

const EMPTY_FILTERS: AdminInvestigationCandidateFilters = {
  client_hint: "",
  business_hint: "",
  amount_min_usd: "",
  amount_max_usd: "",
  created_from: "",
  created_to: "",
  order_status: "",
  support_status_group: "all"
};

function apiFilters(filters: AdminInvestigationCandidateFilters) {
  return {
    ...filters,
    created_from: filters.created_from ? new Date(filters.created_from).toISOString() : "",
    created_to: filters.created_to ? new Date(filters.created_to).toISOString() : ""
  };
}

type ApiCandidateFilters = ReturnType<typeof apiFilters>;

function filtersKey(filters: ApiCandidateFilters) {
  return JSON.stringify(filters);
}

export function useAdminInvestigationCandidatesModel({
  request,
  setNotice,
  setView,
  openOrder,
  openCaseFile
}: {
  request: RequestFn;
  setNotice: (notice: string) => void;
  setView: (view: AdminWebView) => void;
  openOrder: (id: string) => Promise<void>;
  openCaseFile: (anchor: { id: string; type: string }) => Promise<void>;
}) {
  const [filters, setFilters] = useState<AdminInvestigationCandidateFilters>(EMPTY_FILTERS);
  const [results, setResults] = useState<AdminInvestigationCandidatesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const executedFiltersRef = useRef<ApiCandidateFilters | null>(null);
  const requestSequenceRef = useRef(0);

  const setFilter = useCallback(
    (name: keyof AdminInvestigationCandidateFilters, value: string) => {
      requestSequenceRef.current += 1;
      executedFiltersRef.current = null;
      setResults(null);
      setLoading(false);
      setFilters((current) => ({ ...current, [name]: value }));
    },
    []
  );

  const openAdvancedInvestigation = useCallback(() => {
    setView("investigation-candidates");
  }, [setView]);

  const searchCandidates = useCallback(
    async ({ append = false }: { append?: boolean } = {}) => {
      if (loading) {
        return;
      }
      const currentFilters = apiFilters(filters);
      let requestFilters = currentFilters;
      let cursor: string | undefined;
      if (append) {
        const executedFilters = executedFiltersRef.current;
        if (
          !results?.next_cursor ||
          !executedFilters ||
          filtersKey(executedFilters) !== filtersKey(currentFilters)
        ) {
          executedFiltersRef.current = null;
          setResults(null);
          setNotice("Los filtros cambiaron. Ejecuta una busqueda nueva.");
          return;
        }
        requestFilters = executedFilters;
        cursor = results.next_cursor;
      }
      const requestSequence = requestSequenceRef.current + 1;
      requestSequenceRef.current = requestSequence;
      setLoading(true);
      setView("investigation-candidates");
      try {
        const data = await searchAdminInvestigationCandidates<AdminInvestigationCandidatesResponse>(
          request,
          requestFilters,
          cursor
        );
        if (requestSequence !== requestSequenceRef.current) {
          return;
        }
        if (!append) {
          executedFiltersRef.current = requestFilters;
        }
        setResults((current) =>
          append && current
            ? { ...data, items: [...current.items, ...data.items] }
            : data
        );
        setNotice(
          data.items.length
            ? `Encontramos ${data.items.length} orden(es) candidata(s) en esta pagina.`
            : "No encontramos ordenes con todos esos filtros."
        );
      } catch (error) {
        if (requestSequence !== requestSequenceRef.current) {
          return;
        }
        setNotice(error instanceof Error ? error.message : "No pudimos completar la busqueda avanzada.");
      } finally {
        if (requestSequence === requestSequenceRef.current) {
          setLoading(false);
        }
      }
    },
    [filters, loading, request, results?.next_cursor, setNotice, setView]
  );

  const investigateCandidate = useCallback(
    async (candidate: AdminInvestigationCandidate) => {
      await openCaseFile({ type: "order", id: candidate.order_id });
    },
    [openCaseFile]
  );

  return {
    candidateFilters: filters,
    candidateResults: results,
    candidateLoading: loading,
    setCandidateFilter: setFilter,
    openAdvancedInvestigation,
    searchInvestigationCandidates: searchCandidates,
    openCandidateOrder: openOrder,
    investigateCandidate
  };
}
