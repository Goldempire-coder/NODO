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
import { useAdminInvestigationModel } from "./admin-web/useAdminInvestigationModel";
import { useAdminInvestigationCaseFileModel } from "./admin-web/useAdminInvestigationCaseFileModel";
import { useAdminInvestigationCandidatesModel } from "./admin-web/useAdminInvestigationCandidatesModel";
import { useVisibleAdminPolling } from "./admin-web/useVisibleAdminPolling";
import type { PublicUser } from "../types/auth";

const ADMIN_BACKGROUND_REFRESH_MS = 15000;
const ADMIN_SUPPORT_REFRESH_MS = 5000;
const ADMIN_DETAIL_BACK_VIEWS: AdminWebView[] = [
  "business-detail",
  "case-file",
  "intake-detail",
  "order-detail",
  "staff-detail",
  "support",
  "user-detail"
];

export function useAdminWebModel({ token, user }: { user: PublicUser; token: string }) {
  const [view, setView] = useState<AdminWebView>("dashboard");
  const [adminBackStack, setAdminBackStack] = useState<AdminWebView[]>([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("Admin Web separado. Backend RBAC valida cada accion.");
  const clearNoticeIf = useCallback((expected: string) => {
    setNotice((current) => current === expected ? "" : current);
  }, []);

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
  const pushAdminBackView = useCallback((returnView: AdminWebView) => {
    setAdminBackStack((current) => {
      if (current[current.length - 1] === returnView) {
        return current;
      }
      return [...current, returnView];
    });
  }, []);
  const adminBackTarget = adminBackStack[adminBackStack.length - 1] ?? null;
  const adminCanGoBack = Boolean(adminBackTarget);
  const adminBackLabel = !adminBackTarget || adminBackTarget === "investigation" ? "Volver a buscar" : "Volver";
  const goBackAdminView = useCallback(() => {
    if (!adminBackTarget) {
      return;
    }
    setAdminBackStack((current) => current.slice(0, -1));
    setView(adminBackTarget);
  }, [adminBackTarget]);

  useEffect(() => {
    if (!ADMIN_DETAIL_BACK_VIEWS.includes(view)) {
      setAdminBackStack([]);
    }
  }, [view]);

  const overview = useAdminOverviewModel({
    adminMutable,
    adminReadable,
    queueCriticalAction: criticalAction.queueCriticalAction,
    reason: criticalAction.reason,
    request,
    setBusy,
    clearNoticeIf,
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
    setView,
    view
  });

  const support = useAdminSupportModel({
    adminMutable,
    queueCriticalAction: criticalAction.queueCriticalAction,
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

  const investigationCaseFile = useAdminInvestigationCaseFileModel({
    pushBackView: pushAdminBackView,
    request,
    setNotice,
    setView,
    handlers: {
      openUser: users.openUser,
      openBusiness: businessIntake.openBusiness,
      openBusinessIntake: businessIntake.openBusinessIntake,
      openOrder: ordersDisputes.openOrder,
      openSupportTicket: support.openSupportTicket
    }
  });

  const investigation = useAdminInvestigationModel({
    pushBackView: pushAdminBackView,
    request,
    setBusy,
    setNotice,
    setView,
    handlers: {
      openUser: users.openUser,
      openBusiness: businessIntake.openBusiness,
      openBusinessIntake: businessIntake.openBusinessIntake,
      openOrder: ordersDisputes.openOrder,
      openSupportTicket: support.openSupportTicket,
      openCaseFile: investigationCaseFile.openCaseFile
    }
  });

  const investigationCandidates = useAdminInvestigationCandidatesModel({
    request,
    setNotice,
    setView,
    openOrder: ordersDisputes.openOrder,
    openCaseFile: investigationCaseFile.openCaseFile
  });

  const notifications = useAdminNotificationsModel({
    adminMutable,
    request,
    setNotice,
    handlers: {
      openBusinessIntake: businessIntake.openBusinessIntake,
      openSupportTicket: support.openSupportTicket,
      openOrder: ordersDisputes.openOrder,
      loadCreditPurchases: credits.loadCreditPurchases,
      loadJobs: overview.loadJobs,
      setView
    }
  });

  useEffect(() => {
    void overview.loadDashboard();
  }, [overview.loadDashboard]);

  useVisibleAdminPolling({
    enabled: adminReadable,
    intervalMs: ADMIN_BACKGROUND_REFRESH_MS,
    poll: async (isCurrent) => {
      await Promise.all([
        overview.refreshDashboardSnapshot(isCurrent),
        notifications.panelOpen
          ? notifications.loadNotifications("unread", isCurrent, true)
          : notifications.loadUnreadCount(isCurrent)
      ]);
    }
  });

  useVisibleAdminPolling({
    enabled: adminReadable && view === "support",
    intervalMs: ADMIN_SUPPORT_REFRESH_MS,
    poll: support.refreshSupportWorkspace
  });

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
      { view: "businesses" as const, label: "Negocios", action: () => businessIntake.loadBusinesses("", "") },
      { view: "users" as const, label: "Clientes", action: () => users.loadUsers() },
      { view: "orders" as const, label: "Ordenes", action: () => ordersDisputes.loadOrders("", "") },
      { view: "disputes" as const, label: "Disputas", action: () => ordersDisputes.loadDisputes("open") },
      { view: "credit-purchases" as const, label: "Creditos", action: () => credits.loadCreditPurchases("pending_manual_review") },
      { view: "audit-logs" as const, label: "Audit", action: audit.loadAuditLogs },
      { view: "metrics" as const, label: "Metricas", action: overview.loadMetrics },
      { view: "investigation" as const, label: "Buscar", action: () => investigation.searchInvestigation() },
      { view: "jobs" as const, label: "Jobs", action: overview.loadJobs },
      {
        view: "intake" as const,
        label: "Intake",
        badge: overview.dashboard?.queues.pending_business_intakes || 0,
        action: () => businessIntake.loadBusinessIntakes("submitted")
      },
      { view: "support" as const, label: "Soporte", badge: notifications.supportUnreadCount, action: () => support.loadSupportTickets("active") },
      { view: "staff" as const, label: "Staff", action: () => staff.loadStaff("") }
    ],
    [audit.loadAuditLogs, businessIntake.loadBusinesses, businessIntake.loadBusinessIntakes, credits.loadCreditPurchases, investigation.searchInvestigation, notifications.supportUnreadCount, ordersDisputes.loadDisputes, ordersDisputes.loadOrders, overview.dashboard?.queues.pending_business_intakes, overview.loadDashboard, overview.loadIncidentConsole, overview.loadJobs, overview.loadMetrics, overview.loadUXFriction, staff.loadStaff, support.loadSupportTickets, users.loadUsers]
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
    investigationQuery: investigation.investigationQuery,
    setInvestigationQuery: investigation.setInvestigationQuery,
    investigationResults: investigation.investigationResults,
    investigationSearched: investigation.investigationSearched,
    adminBackLabel,
    adminCanGoBack,
    candidateFilters: investigationCandidates.candidateFilters,
    candidateResults: investigationCandidates.candidateResults,
    candidateLoading: investigationCandidates.candidateLoading,
    caseFile: investigationCaseFile.caseFile,
    caseFileLoading: investigationCaseFile.caseFileLoading,
    caseFileSectionLoading: investigationCaseFile.caseFileSectionLoading,
    businesses: businessIntake.businesses,
    businessesLoadingMore: businessIntake.businessesLoadingMore,
    businessesNextCursor: businessIntake.businessesNextCursor,
    selectedBusiness: businessIntake.selectedBusiness,
    businessAccessActionFeedback: businessIntake.businessAccessActionFeedback,
    businessAccessDiagnosticPending: businessIntake.businessAccessDiagnosticPending,
    businessAccessLinks: businessIntake.businessAccessLinks,
    businessCapacityDraft: businessIntake.businessCapacityDraft,
    businessOperationalCapacity: businessIntake.businessOperationalCapacity,
    businessOperationalCapacityDraft: businessIntake.businessOperationalCapacityDraft,
    users: users.users,
    usersLoadingMore: users.usersLoadingMore,
    usersNextCursor: users.usersNextCursor,
    selectedUser: users.selectedUser,
    revealedUserPhone: users.revealedUserPhone,
    orders: ordersDisputes.orders,
    ordersLoadingMore: ordersDisputes.ordersLoadingMore,
    ordersNextCursor: ordersDisputes.ordersNextCursor,
    selectedOrder: ordersDisputes.selectedOrder,
    orderChatEvidence: ordersDisputes.evidence,
    orderChatEvidenceError: ordersDisputes.error,
    orderChatEvidenceLoading: ordersDisputes.loading,
    orderChatEvidenceLoadingMore: ordersDisputes.loadingMore,
    disputes: ordersDisputes.disputes,
    disputesLoadingMore: ordersDisputes.disputesLoadingMore,
    disputesNextCursor: ordersDisputes.disputesNextCursor,
    selectedDispute: ordersDisputes.selectedDispute,
    auditLogs: audit.auditLogs,
    auditLogsLoadingMore: audit.auditLogsLoadingMore,
    auditLogsNextCursor: audit.auditLogsNextCursor,
    creditPurchases: credits.creditPurchases,
    creditPurchasesLoadingMore: credits.creditPurchasesLoadingMore,
    creditPurchasesNextCursor: credits.creditPurchasesNextCursor,
    selectedCreditPurchase: credits.selectedCreditPurchase,
    setSelectedCreditPurchase: credits.setSelectedCreditPurchase,
    jobRuns: overview.jobRuns,
    jobRunsLoadingMore: overview.jobRunsLoadingMore,
    jobRunsNextCursor: overview.jobRunsNextCursor,
    businessIntakes: businessIntake.businessIntakes,
    businessIntakesLoadingMore: businessIntake.businessIntakesLoadingMore,
    businessIntakesNextCursor: businessIntake.businessIntakesNextCursor,
    selectedBusinessIntake: businessIntake.selectedBusinessIntake,
    intakeEditDraft: businessIntake.intakeEditDraft,
    supportTickets: support.supportTickets,
    supportTicketsLoadingMore: support.supportTicketsLoadingMore,
    supportMessagesLoadingMore: support.supportMessagesLoadingMore,
    supportTicketsNextCursor: support.supportTicketsNextCursor,
    selectedSupportTicket: support.selectedSupportTicket,
    supportFilter: support.supportFilter,
    setSupportFilter: support.setSupportFilter,
    supportReply: support.supportReply,
    setSupportReply: support.setSupportReply,
    sendingSupportReply: support.sendingSupportReply,
    supportAttachmentLink: support.supportAttachmentLink,
    supportAttachmentUrl: support.supportAttachmentUrl,
    supportAssignees: support.supportAssignees,
    supportAssigneesLoaded: support.supportAssigneesLoaded,
    supportAssigneesLoading: support.supportAssigneesLoading,
    supportAssigneesTruncated: support.supportAssigneesTruncated,
    supportAssigneeUserId: support.supportAssigneeUserId,
    setSupportAssigneeUserId: support.setSupportAssigneeUserId,
    selectedSupportHasAssignee: support.selectedSupportHasAssignee,
    supportAssignmentReason: support.supportAssignmentReason,
    setSupportAssignmentReason: support.setSupportAssignmentReason,
    assigningSupportTicketId: support.assigningSupportTicketId,
    publicationHoldReleaseError: support.publicationHoldReleaseError,
    publicationHoldReleaseReason: support.publicationHoldReleaseReason,
    releasingPublicationHoldId: support.releasingPublicationHoldId,
    setPublicationHoldReleaseReason: support.setPublicationHoldReleaseReason,
    staff: staff.staff,
    selectedStaff: staff.selectedStaff,
    staffActivity: staff.staffActivity,
    staffFilters: staff.staffFilters,
    setStaffFilters: staff.setStaffFilters,
    staffInvite: staff.staffInvite,
    setStaffInvite: staff.setStaffInvite,
    adminNotifications: notifications.notifications,
    adminNotificationsLoadingMore: notifications.notificationsLoadingMore,
    adminNotificationsNextCursor: notifications.notificationsNextCursor,
    adminNotificationsUnreadCount: notifications.unreadCount,
    adminNotificationsUnreadState: notifications.unreadCountState,
    adminNotificationsPanelOpen: notifications.panelOpen,
    adminNotificationBusyId: notifications.notificationBusyId,
    adminSupportUnreadCount: notifications.supportUnreadCount,
    businessFilter: businessIntake.businessFilter,
    businessSearchFilter: businessIntake.businessSearchFilter,
    setBusinessFilter: businessIntake.setBusinessFilter,
    setBusinessSearchFilter: businessIntake.setBusinessSearchFilter,
    setBusinessCapacityDraft: businessIntake.setBusinessCapacityDraft,
    setBusinessOperationalCapacityDraft: businessIntake.setBusinessOperationalCapacityDraft,
    userFilters: users.userFilters,
    setUserFilters: users.setUserFilters,
    intakeFilter: businessIntake.intakeFilter,
    intakeReadinessFilter: businessIntake.intakeReadinessFilter,
    setIntakeFilter: businessIntake.setIntakeFilter,
    setIntakeReadinessFilter: businessIntake.setIntakeReadinessFilter,
    orderFilter: ordersDisputes.orderFilter,
    orderCodeFilter: ordersDisputes.orderCodeFilter,
    setOrderFilter: ordersDisputes.setOrderFilter,
    setOrderCodeFilter: ordersDisputes.setOrderCodeFilter,
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
    stuckOrderResolutionPreview: ordersDisputes.stuckOrderResolutionPreview,
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
    searchInvestigation: investigation.searchInvestigation,
    clearInvestigationSearch: investigation.clearInvestigationSearch,
    goBackAdminView,
    openInvestigationResult: investigation.openInvestigationResult,
    openInvestigationCaseFile: investigation.openInvestigationCaseFile,
    setCandidateFilter: investigationCandidates.setCandidateFilter,
    openAdvancedInvestigation: investigationCandidates.openAdvancedInvestigation,
    searchInvestigationCandidates: investigationCandidates.searchInvestigationCandidates,
    openCandidateOrder: investigationCandidates.openCandidateOrder,
    investigateCandidate: investigationCandidates.investigateCandidate,
    loadCaseFileSection: investigationCaseFile.loadCaseFileSection,
    openCaseFileRoute: investigationCaseFile.openCaseFileRoute,
    loadBusinesses: businessIntake.loadBusinesses,
    loadMoreBusinesses: businessIntake.loadMoreBusinesses,
    loadPendingBusinesses: businessIntake.loadPendingBusinesses,
    openBusiness: businessIntake.openBusiness,
    submitBusinessCapacity: businessIntake.submitBusinessCapacity,
    submitBusinessOperationalCapacity: businessIntake.submitBusinessOperationalCapacity,
    openDocument: businessIntake.openDocument,
    createBusinessOwnerAccessLink: businessIntake.createBusinessOwnerAccessLink,
    changeBusinessStatus: businessIntake.changeBusinessStatus,
    changeBusinessOwnerUserStatus: businessIntake.changeBusinessOwnerUserStatus,
    changeBusinessAccessLink: businessIntake.changeBusinessAccessLink,
    loadUsers: users.loadUsers,
    loadMoreUsers: users.loadMoreUsers,
    openUser: users.openUser,
    changeUserStatus: users.changeUserStatus,
    revealUserPhone: users.revealUserPhone,
    loadOrders: ordersDisputes.loadOrders,
    loadMoreOrders: ordersDisputes.loadMoreOrders,
    openOrder: ordersDisputes.openOrder,
    loadOlderOrderChatEvidence: ordersDisputes.loadOlderOrderChatEvidence,
    loadNewerOrderChatEvidence: ordersDisputes.loadNewerOrderChatEvidence,
    retryOrderChatEvidence: ordersDisputes.retryOrderChatEvidence,
    loadDisputes: ordersDisputes.loadDisputes,
    loadMoreDisputes: ordersDisputes.loadMoreDisputes,
    openDispute: ordersDisputes.openDispute,
    resolveDispute: ordersDisputes.resolveDispute,
    resolveAdminStuckOrder: ordersDisputes.resolveAdminStuckOrder,
    loadAuditLogs: audit.loadAuditLogs,
    loadMoreAuditLogs: audit.loadMoreAuditLogs,
    loadCreditPurchases: credits.loadCreditPurchases,
    loadMoreCreditPurchases: credits.loadMoreCreditPurchases,
    reviewCreditPurchase: credits.reviewCreditPurchase,
    submitAdjustment: credits.submitAdjustment,
    loadJobs: overview.loadJobs,
    loadMoreJobs: overview.loadMoreJobs,
    dryRunJobs: overview.dryRunJobs,
    loadBusinessIntakes: businessIntake.loadBusinessIntakes,
    loadMoreBusinessIntakes: businessIntake.loadMoreBusinessIntakes,
    openBusinessIntake: businessIntake.openBusinessIntake,
    openBusinessIntakeDocument: businessIntake.openBusinessIntakeDocument,
    saveBusinessIntakeManual: businessIntake.saveBusinessIntakeManual,
    approveBusinessFromIntake: businessIntake.approveBusinessFromIntake,
    createBusinessFromIntake: businessIntake.createBusinessFromIntake,
    deleteBusinessIntake: businessIntake.deleteBusinessIntake,
    loadSupportTickets: support.loadSupportTickets,
    loadMoreSupportTickets: support.loadMoreSupportTickets,
    loadMoreSupportMessages: support.loadMoreSupportMessages,
    openSupportTicket: support.openSupportTicket,
    refreshSupportWorkspace: support.refreshSupportWorkspace,
    refreshSelectedSupportTicket: support.refreshSelectedSupportTicket,
    replySupportTicket: support.replySupportTicket,
    loadSupportAssignees: support.loadSupportAssignees,
    assignSupportTicket: support.assignSupportTicket,
    requestPublicationHoldRelease: support.requestPublicationHoldRelease,
    changeSupportStatus: support.changeSupportStatus,
    openSupportAttachment: support.openSupportAttachment,
    loadStaff: staff.loadStaff,
    openStaff: staff.openStaff,
    submitStaffInvite: staff.submitStaffInvite,
    changeStaffStatus: staff.changeStaffStatus,
    replaceStaffPermissions: staff.replaceStaffPermissions,
    toggleAdminNotifications: notifications.togglePanel,
    loadAdminNotifications: notifications.loadNotifications,
    loadMoreAdminNotifications: notifications.loadMoreNotifications,
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
