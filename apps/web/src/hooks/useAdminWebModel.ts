"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiRequest } from "../api/client";
import { canMutateAdmin, canReadAdmin } from "./admin-web/adminWebAccess";
import type { AdminWebView, RequestFn } from "./admin-web/adminWebTypes";
import { useAdminCriticalAction } from "./admin-web/useAdminCriticalAction";
import { useAdminAuditLogsModel } from "./admin-web/useAdminAuditLogsModel";
import { useAdminBusinessIntakeModel } from "./admin-web/useAdminBusinessIntakeModel";
import { useAdminCreditsModel } from "./admin-web/useAdminCreditsModel";
import { useAdminOverviewModel } from "./admin-web/useAdminOverviewModel";
import { useAdminOrdersDisputesModel } from "./admin-web/useAdminOrdersDisputesModel";
import type { PublicUser } from "../types/auth";

export function useAdminWebModel({ token, user }: { user: PublicUser; token: string }) {
  const [view, setView] = useState<AdminWebView>("dashboard");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("Admin Web separado. Backend RBAC valida cada accion.");

  const adminReadable = canReadAdmin(user);
  const adminMutable = canMutateAdmin(user);

  const request = useCallback<RequestFn>(
    async (path, options = {}) =>
      apiRequest(path, token, {
        ...options,
        headers: {
          "X-NODO-Surface": "admin_web",
          ...(options.headers || {})
        }
      }),
    [token]
  );

  const criticalAction = useAdminCriticalAction({ setBusy, setNotice });

  const overview = useAdminOverviewModel({
    adminMutable,
    adminReadable,
    queueCriticalAction: criticalAction.queueCriticalAction,
    request,
    setBusy,
    setNotice,
    setView
  });

  const businessIntake = useAdminBusinessIntakeModel({
    adminMutable,
    queueCriticalAction: criticalAction.queueCriticalAction,
    reason: criticalAction.reason,
    request,
    setBusy,
    setNotice,
    setReason: criticalAction.setReason,
    setView
  });

  const ordersDisputes = useAdminOrdersDisputesModel({
    adminMutable,
    queueCriticalAction: criticalAction.queueCriticalAction,
    reason: criticalAction.reason,
    request,
    setBusy,
    setNotice,
    setReason: criticalAction.setReason,
    setView
  });

  const credits = useAdminCreditsModel({
    adminMutable,
    queueCriticalAction: criticalAction.queueCriticalAction,
    reason: criticalAction.reason,
    request,
    setBusy,
    setNotice,
    setReason: criticalAction.setReason,
    setView
  });

  const audit = useAdminAuditLogsModel({
    request,
    setBusy,
    setNotice,
    setView
  });

  useEffect(() => {
    void overview.loadDashboard();
  }, [overview.loadDashboard]);

  const navigation = useMemo(
    () => [
      { view: "dashboard" as const, label: "Dashboard", action: overview.loadDashboard },
      { view: "businesses" as const, label: "Negocios", action: businessIntake.loadPendingBusinesses },
      { view: "orders" as const, label: "Ordenes", action: () => ordersDisputes.loadOrders("") },
      { view: "disputes" as const, label: "Disputas", action: () => ordersDisputes.loadDisputes("open") },
      { view: "credit-purchases" as const, label: "Creditos", action: () => credits.loadCreditPurchases("pending_manual_review") },
      { view: "audit-logs" as const, label: "Audit", action: audit.loadAuditLogs },
      { view: "metrics" as const, label: "Metricas", action: overview.loadMetrics },
      { view: "jobs" as const, label: "Jobs", action: overview.loadJobs },
      { view: "intake" as const, label: "Intake", action: () => businessIntake.loadBusinessIntakes("submitted") },
      { view: "support-placeholder" as const, label: "Soporte", action: () => setView("support-placeholder") }
    ],
    [audit.loadAuditLogs, businessIntake.loadBusinessIntakes, businessIntake.loadPendingBusinesses, credits.loadCreditPurchases, ordersDisputes.loadDisputes, ordersDisputes.loadOrders, overview.loadDashboard, overview.loadJobs, overview.loadMetrics]
  );

  return {
    user,
    view,
    setView,
    busy,
    notice,
    adminReadable,
    adminMutable,
    dashboard: overview.dashboard,
    metrics: overview.metrics,
    businesses: businessIntake.businesses,
    selectedBusiness: businessIntake.selectedBusiness,
    orders: ordersDisputes.orders,
    selectedOrder: ordersDisputes.selectedOrder,
    disputes: ordersDisputes.disputes,
    selectedDispute: ordersDisputes.selectedDispute,
    auditLogs: audit.auditLogs,
    creditPurchases: credits.creditPurchases,
    selectedCreditPurchase: credits.selectedCreditPurchase,
    setSelectedCreditPurchase: credits.setSelectedCreditPurchase,
    jobRuns: overview.jobRuns,
    businessIntakes: businessIntake.businessIntakes,
    selectedBusinessIntake: businessIntake.selectedBusinessIntake,
    businessFilter: businessIntake.businessFilter,
    setBusinessFilter: businessIntake.setBusinessFilter,
    intakeFilter: businessIntake.intakeFilter,
    setIntakeFilter: businessIntake.setIntakeFilter,
    orderFilter: ordersDisputes.orderFilter,
    setOrderFilter: ordersDisputes.setOrderFilter,
    disputeFilter: ordersDisputes.disputeFilter,
    setDisputeFilter: ordersDisputes.setDisputeFilter,
    auditFilter: audit.auditFilter,
    setAuditFilter: audit.setAuditFilter,
    creditFilter: credits.creditFilter,
    setCreditFilter: credits.setCreditFilter,
    reason: criticalAction.reason,
    setReason: criticalAction.setReason,
    intakePublicBusinessName: businessIntake.intakePublicBusinessName,
    setIntakePublicBusinessName: businessIntake.setIntakePublicBusinessName,
    resolutionType: ordersDisputes.resolutionType,
    setResolutionType: ordersDisputes.setResolutionType,
    adjustmentBusinessId: credits.adjustmentBusinessId,
    setAdjustmentBusinessId: credits.setAdjustmentBusinessId,
    adjustmentAmount: credits.adjustmentAmount,
    setAdjustmentAmount: credits.setAdjustmentAmount,
    adjustmentDirection: credits.adjustmentDirection,
    setAdjustmentDirection: credits.setAdjustmentDirection,
    pendingAction: criticalAction.pendingAction,
    setPendingAction: criticalAction.setPendingAction,
    navigation,
    loadDashboard: overview.loadDashboard,
    loadMetrics: overview.loadMetrics,
    loadBusinesses: businessIntake.loadBusinesses,
    loadPendingBusinesses: businessIntake.loadPendingBusinesses,
    openBusiness: businessIntake.openBusiness,
    reviewBusiness: businessIntake.reviewBusiness,
    openDocument: businessIntake.openDocument,
    loadOrders: ordersDisputes.loadOrders,
    openOrder: ordersDisputes.openOrder,
    loadDisputes: ordersDisputes.loadDisputes,
    openDispute: ordersDisputes.openDispute,
    resolveDispute: ordersDisputes.resolveDispute,
    loadAuditLogs: audit.loadAuditLogs,
    loadCreditPurchases: credits.loadCreditPurchases,
    reviewCreditPurchase: credits.reviewCreditPurchase,
    submitAdjustment: credits.submitAdjustment,
    loadJobs: overview.loadJobs,
    dryRunJobs: overview.dryRunJobs,
    loadBusinessIntakes: businessIntake.loadBusinessIntakes,
    openBusinessIntake: businessIntake.openBusinessIntake,
    createBusinessFromIntake: businessIntake.createBusinessFromIntake,
    deleteBusinessIntake: businessIntake.deleteBusinessIntake,
    confirmPendingAction: criticalAction.confirmPendingAction
  };
}

export type { AdminWebView } from "./admin-web/adminWebTypes";
export type { AdminBusinessIntakeDetail, AdminBusinessIntakeSummary, BusinessSummaryForAdmin } from "./admin-web/useAdminBusinessIntakeModel";
export type { AdminWebDisputeDetail, AdminWebOrderDetail } from "./admin-web/useAdminOrdersDisputesModel";
export type { AdminWebJobRun } from "./admin-web/useAdminOverviewModel";
export type AdminWebModel = ReturnType<typeof useAdminWebModel>;
