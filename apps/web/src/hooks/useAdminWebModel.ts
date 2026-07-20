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
import { useAdminUsersModel } from "./admin-web/useAdminUsersModel";
import { useAdminSupportModel } from "./admin-web/useAdminSupportModel";
import { useAdminStaffModel } from "./admin-web/useAdminStaffModel";
import { useAdminNotificationsModel } from "./admin-web/useAdminNotificationsModel";
import type { PublicUser } from "../types/auth";

const ADMIN_BACKGROUND_REFRESH_MS = 15000;
const ADMIN_SUPPORT_REFRESH_MS = 5000;

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
    reason: criticalAction.reason,
    request,
    setBusy,
    setNotice,
    setReason: criticalAction.setReason,
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

  const users = useAdminUsersModel({
    adminMutable,
    queueCriticalAction: criticalAction.queueCriticalAction,
    reason: criticalAction.reason,
    request,
    setBusy,
    setNotice,
    setReason: criticalAction.setReason,
    setView
  });

  const support = useAdminSupportModel({
    request,
    setBusy,
    setNotice,
    setView
  });

  const staff = useAdminStaffModel({
    request,
    setBusy,
    setNotice,
    setView,
    queueCriticalAction: criticalAction.queueCriticalAction,
    reason: criticalAction.reason,
    setReason: criticalAction.setReason
  });

  const notifications = useAdminNotificationsModel({
    adminMutable,
    request,
    setNotice,
    handlers: {
      openBusinessIntake: businessIntake.openBusinessIntake,
      openSupportTicket: support.openSupportTicket,
      loadCreditPurchases: credits.loadCreditPurchases,
      loadJobs: overview.loadJobs,
      setView
    }
  });

  useEffect(() => {
    void overview.loadDashboard();
  }, [overview.loadDashboard]);

  useEffect(() => {
    if (!adminReadable) {
      return;
    }
    const interval = window.setInterval(() => {
      void overview.refreshDashboardSnapshot();
      if (notifications.panelOpen) {
        void notifications.loadNotifications("unread");
      } else {
        void notifications.loadUnreadCount();
      }
    }, ADMIN_BACKGROUND_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [adminReadable, notifications.loadNotifications, notifications.loadUnreadCount, notifications.panelOpen, overview.refreshDashboardSnapshot]);

  useEffect(() => {
    if (!adminReadable || view !== "support") {
      return;
    }
    const interval = window.setInterval(() => {
      void support.refreshSupportWorkspace();
    }, ADMIN_SUPPORT_REFRESH_MS);
    return () => window.clearInterval(interval);
  }, [adminReadable, support.refreshSupportWorkspace, view]);

  useEffect(() => {
    if (!adminReadable) {
      return;
    }
    void notifications.loadUnreadCount();
  }, [adminReadable, notifications.loadUnreadCount]);

  const navigation = useMemo(
    () => [
      { view: "dashboard" as const, label: "Dashboard", action: overview.loadDashboard },
      { view: "incidents" as const, label: "Incidentes", action: overview.loadIncidentConsole },
      { view: "ux-friction" as const, label: "UX", action: overview.loadUXFriction },
      { view: "businesses" as const, label: "Negocios", action: () => businessIntake.loadBusinesses("") },
      { view: "users" as const, label: "Clientes", action: () => users.loadUsers() },
      { view: "orders" as const, label: "Ordenes", action: () => ordersDisputes.loadOrders("") },
      { view: "disputes" as const, label: "Disputas", action: () => ordersDisputes.loadDisputes("open") },
      { view: "credit-purchases" as const, label: "Creditos", action: () => credits.loadCreditPurchases("pending_manual_review") },
      { view: "audit-logs" as const, label: "Audit", action: audit.loadAuditLogs },
      { view: "metrics" as const, label: "Metricas", action: overview.loadMetrics },
      { view: "jobs" as const, label: "Jobs", action: overview.loadJobs },
      {
        view: "intake" as const,
        label: "Intake",
        badge: overview.dashboard?.queues.pending_business_intakes || 0,
        action: () => businessIntake.loadBusinessIntakes("submitted")
      },
      { view: "support" as const, label: "Soporte", action: () => support.loadSupportTickets("active") },
      { view: "staff" as const, label: "Staff", action: () => staff.loadStaff("") }
    ],
    [audit.loadAuditLogs, businessIntake.loadBusinesses, businessIntake.loadBusinessIntakes, credits.loadCreditPurchases, ordersDisputes.loadDisputes, ordersDisputes.loadOrders, overview.dashboard?.queues.pending_business_intakes, overview.loadDashboard, overview.loadIncidentConsole, overview.loadJobs, overview.loadMetrics, overview.loadUXFriction, staff.loadStaff, support.loadSupportTickets, users.loadUsers]
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
    incidentConsole: overview.incidentConsole,
    uxFriction: overview.uxFriction,
    emergencyMessage: overview.emergencyMessage,
    setEmergencyMessage: overview.setEmergencyMessage,
    metrics: overview.metrics,
    businesses: businessIntake.businesses,
    selectedBusiness: businessIntake.selectedBusiness,
    businessAccessLinks: businessIntake.businessAccessLinks,
    businessCapacityDraft: businessIntake.businessCapacityDraft,
    users: users.users,
    selectedUser: users.selectedUser,
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
    intakeEditDraft: businessIntake.intakeEditDraft,
    supportTickets: support.supportTickets,
    selectedSupportTicket: support.selectedSupportTicket,
    supportFilter: support.supportFilter,
    setSupportFilter: support.setSupportFilter,
    supportReply: support.supportReply,
    setSupportReply: support.setSupportReply,
    sendingSupportReply: support.sendingSupportReply,
    supportAttachmentUrl: support.supportAttachmentUrl,
    staff: staff.staff,
    selectedStaff: staff.selectedStaff,
    staffActivity: staff.staffActivity,
    staffFilters: staff.staffFilters,
    setStaffFilters: staff.setStaffFilters,
    staffInvite: staff.staffInvite,
    setStaffInvite: staff.setStaffInvite,
    adminNotifications: notifications.notifications,
    adminNotificationsUnreadCount: notifications.unreadCount,
    adminNotificationsPanelOpen: notifications.panelOpen,
    adminNotificationBusyId: notifications.notificationBusyId,
    businessFilter: businessIntake.businessFilter,
    setBusinessFilter: businessIntake.setBusinessFilter,
    setBusinessCapacityDraft: businessIntake.setBusinessCapacityDraft,
    userFilters: users.userFilters,
    setUserFilters: users.setUserFilters,
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
    setIntakeEditDraft: businessIntake.setIntakeEditDraft,
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
    loadIncidentConsole: overview.loadIncidentConsole,
    loadUXFriction: overview.loadUXFriction,
    activateEmergencyMode: overview.activateEmergencyMode,
    deactivateEmergencyMode: overview.deactivateEmergencyMode,
    loadEmergencyMode: overview.loadEmergencyMode,
    loadMetrics: overview.loadMetrics,
    loadBusinesses: businessIntake.loadBusinesses,
    loadPendingBusinesses: businessIntake.loadPendingBusinesses,
    openBusiness: businessIntake.openBusiness,
    submitBusinessCapacity: businessIntake.submitBusinessCapacity,
    openDocument: businessIntake.openDocument,
    createBusinessOwnerAccessLink: businessIntake.createBusinessOwnerAccessLink,
    changeBusinessAccessLink: businessIntake.changeBusinessAccessLink,
    loadUsers: users.loadUsers,
    openUser: users.openUser,
    changeUserStatus: users.changeUserStatus,
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
    openBusinessIntakeDocument: businessIntake.openBusinessIntakeDocument,
    saveBusinessIntakeManual: businessIntake.saveBusinessIntakeManual,
    approveBusinessFromIntake: businessIntake.approveBusinessFromIntake,
    createBusinessFromIntake: businessIntake.createBusinessFromIntake,
    deleteBusinessIntake: businessIntake.deleteBusinessIntake,
    loadSupportTickets: support.loadSupportTickets,
    openSupportTicket: support.openSupportTicket,
    refreshSupportWorkspace: support.refreshSupportWorkspace,
    refreshSelectedSupportTicket: support.refreshSelectedSupportTicket,
    replySupportTicket: support.replySupportTicket,
    changeSupportStatus: support.changeSupportStatus,
    openSupportAttachment: support.openSupportAttachment,
    loadStaff: staff.loadStaff,
    openStaff: staff.openStaff,
    submitStaffInvite: staff.submitStaffInvite,
    changeStaffStatus: staff.changeStaffStatus,
    replaceStaffPermissions: staff.replaceStaffPermissions,
    toggleAdminNotifications: notifications.togglePanel,
    loadAdminNotifications: notifications.loadNotifications,
    openAdminNotification: notifications.openNotification,
    markAdminNotificationRead: notifications.markRead,
    dismissAdminNotification: notifications.dismiss,
    resolveAdminNotification: notifications.resolve,
    confirmPendingAction: criticalAction.confirmPendingAction
  };
}

export type { AdminWebView } from "./admin-web/adminWebTypes";
export type { AdminBusinessIntakeDetail, AdminBusinessIntakeSummary, BusinessSummaryForAdmin } from "./admin-web/useAdminBusinessIntakeModel";
export type { AdminWebDisputeDetail, AdminWebOrderDetail } from "./admin-web/useAdminOrdersDisputesModel";
export type { AdminWebJobRun } from "./admin-web/useAdminOverviewModel";
export type AdminWebModel = ReturnType<typeof useAdminWebModel>;
