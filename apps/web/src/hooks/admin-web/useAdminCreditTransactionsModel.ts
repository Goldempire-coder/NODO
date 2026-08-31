import { useCallback, useRef, useState } from "react";
import { listAdminCreditTransactions } from "../../api/admin";
import type { AuthenticatedRequest } from "../../api/client";
import type { AdminCreditTransactionItem, AdminCreditTransactionSummary } from "../../types/credits";
import type { CreditsView } from "./adminCreditsTypes";

export type AdminCreditTransactionFilters = {
  financial_status: string;
  payment_method: string;
  business_id: string;
  package_code: string;
  created_from: string;
  created_to: string;
};

const EMPTY_TRANSACTION_FILTERS: AdminCreditTransactionFilters = {
  financial_status: "",
  payment_method: "",
  business_id: "",
  package_code: "",
  created_from: "",
  created_to: ""
};

const EMPTY_TRANSACTION_SUMMARY: AdminCreditTransactionSummary = {
  total_count: 0,
  confirmed_count: 0,
  pending_count: 0,
  review_count: 0,
  failed_count: 0,
  dismissed_count: 0,
  confirmed_amount_usd: "0.00",
  confirmed_credits: 0
};

function appendUniqueTransactions(
  current: AdminCreditTransactionItem[],
  incoming: AdminCreditTransactionItem[]
) {
  const knownIds = new Set(current.map((item) => item.purchase_id));
  return [...current, ...incoming.filter((item) => !knownIds.has(item.purchase_id))];
}

function compactFilters(filters: AdminCreditTransactionFilters) {
  return {
    financial_status: filters.financial_status.trim(),
    payment_method: filters.payment_method.trim(),
    business_id: filters.business_id.trim(),
    package_code: filters.package_code.trim(),
    created_from: filters.created_from.trim(),
    created_to: filters.created_to.trim()
  };
}

export function useAdminCreditTransactionsModel({
  request,
  setBusy,
  setNotice,
  setView
}: {
  request: AuthenticatedRequest;
  setBusy: (busy: boolean) => void;
  setNotice: (notice: string) => void;
  setView: (view: CreditsView) => void;
}) {
  const [creditTransactions, setCreditTransactions] = useState<AdminCreditTransactionItem[]>([]);
  const [creditTransactionsSummary, setCreditTransactionsSummary] = useState<AdminCreditTransactionSummary>(EMPTY_TRANSACTION_SUMMARY);
  const [creditTransactionsNextCursor, setCreditTransactionsNextCursor] = useState<string | null>(null);
  const [creditTransactionsLoadingMore, setCreditTransactionsLoadingMore] = useState(false);
  const [creditTransactionFilters, setCreditTransactionFilters] = useState<AdminCreditTransactionFilters>(EMPTY_TRANSACTION_FILTERS);
  const creditTransactionsRequestEpoch = useRef(0);
  const creditTransactionsQueryRef = useRef(EMPTY_TRANSACTION_FILTERS);

  const loadCreditTransactions = useCallback(async (filters = creditTransactionFilters) => {
    const requestEpoch = ++creditTransactionsRequestEpoch.current;
    const nextFilters = compactFilters(filters);
    setCreditTransactionsLoadingMore(false);
    setBusy(true);
    try {
      const data = await listAdminCreditTransactions(request, nextFilters);
      if (requestEpoch !== creditTransactionsRequestEpoch.current) {
        return;
      }
      setCreditTransactions(data.items);
      setCreditTransactionsSummary(data.summary);
      setCreditTransactionsNextCursor(data.next_cursor);
      setCreditTransactionFilters(nextFilters);
      creditTransactionsQueryRef.current = nextFilters;
      setView("credit-transactions");
      setNotice(data.items.length ? "Registro NODO cargado." : "No hay transacciones de creditos para esos filtros.");
    } catch (error) {
      if (requestEpoch === creditTransactionsRequestEpoch.current) {
        setCreditTransactions([]);
        setCreditTransactionsSummary(EMPTY_TRANSACTION_SUMMARY);
        setCreditTransactionsNextCursor(null);
        setNotice(error instanceof Error ? error.message : "No se pudo cargar el registro NODO.");
      }
    } finally {
      if (requestEpoch === creditTransactionsRequestEpoch.current) {
        setBusy(false);
      }
    }
  }, [creditTransactionFilters, request, setBusy, setNotice, setView]);

  const loadMoreCreditTransactions = useCallback(async () => {
    const cursor = creditTransactionsNextCursor;
    if (!cursor || creditTransactionsLoadingMore) {
      return;
    }
    const requestEpoch = ++creditTransactionsRequestEpoch.current;
    const requestedFilters = creditTransactionsQueryRef.current;
    setCreditTransactionsLoadingMore(true);
    try {
      const data = await listAdminCreditTransactions(request, requestedFilters, cursor);
      if (requestEpoch !== creditTransactionsRequestEpoch.current) {
        return;
      }
      setCreditTransactions((current) => appendUniqueTransactions(current, data.items));
      setCreditTransactionsSummary(data.summary);
      setCreditTransactionsNextCursor(data.next_cursor);
    } catch (error) {
      if (requestEpoch === creditTransactionsRequestEpoch.current) {
        setNotice(error instanceof Error ? error.message : "No se pudieron cargar mas transacciones de creditos.");
      }
    } finally {
      if (requestEpoch === creditTransactionsRequestEpoch.current) {
        setCreditTransactionsLoadingMore(false);
      }
    }
  }, [creditTransactionsLoadingMore, creditTransactionsNextCursor, request, setNotice]);

  return {
    creditTransactionFilters,
    creditTransactions,
    creditTransactionsLoadingMore,
    creditTransactionsNextCursor,
    creditTransactionsSummary,
    loadCreditTransactions,
    loadMoreCreditTransactions,
    setCreditTransactionFilters
  };
}
