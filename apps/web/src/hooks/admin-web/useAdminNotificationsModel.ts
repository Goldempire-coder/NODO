"use client";

import { useCallback, useRef, useState } from "react";
import {
  dismissAdminNotification,
  getAdminNotificationsUnreadCount,
  listAdminNotifications,
  markAdminNotificationRead,
  resolveAdminNotification
} from "../../api/admin";
import type { AdminNotification, AdminNotificationsList } from "../../types/admin";
import { actionStartedAt, recordActionFailed } from "../actionTelemetry";
import type { AdminWebView, RequestFn } from "./adminWebTypes";

type OpenHandlers = {
  openBusinessIntake: (id: string) => Promise<void>;
  openSupportTicket: (id: string) => Promise<void>;
  openOrder: (id: string, highlightMessageId?: string) => Promise<void>;
  loadCreditPurchases: (status?: string) => Promise<void>;
  loadJobs: () => Promise<void>;
  setView: (view: AdminWebView) => void;
};

function routeTarget(notification: AdminNotification): { type: string; id?: string; highlightMessageId?: string } {
  const route = notification.action_route || "";
  if (route.startsWith("admin://business-intake/")) {
    return { type: "business_intake", id: route.replace("admin://business-intake/", "") };
  }
  if (route.startsWith("admin://support-ticket/")) {
    return { type: "support_ticket", id: route.replace("admin://support-ticket/", "") };
  }
  if (route.startsWith("admin://order/")) {
    const highlightMessageId = typeof notification.metadata.message_id === "string" ? notification.metadata.message_id : undefined;
    return { type: "order", id: route.replace("admin://order/", ""), highlightMessageId };
  }
  if (route.startsWith("admin://credit-purchase/")) {
    return { type: "credit_purchase" };
  }
  if (route.startsWith("admin://notification-job/")) {
    return { type: "notification_job" };
  }
  return { type: notification.resource_type, id: notification.resource_id || undefined };
}

export function useAdminNotificationsModel({
  adminMutable,
  handlers,
  request,
  setNotice
}: {
  adminMutable: boolean;
  handlers: OpenHandlers;
  request: RequestFn;
  setNotice: (notice: string) => void;
}) {
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [supportUnreadCount, setSupportUnreadCount] = useState(0);
  const [unreadCountState, setUnreadCountState] = useState<"idle" | "ready" | "stale">("idle");
  const [panelOpen, setPanelOpen] = useState(false);
  const [notificationBusyId, setNotificationBusyId] = useState<string | null>(null);
  const unreadCountInitialized = useRef(false);
  const lastUnreadCount = useRef(0);

  const applyUnreadCount = useCallback((nextCount: number, nextSupportCount: number) => {
    const previousCount = lastUnreadCount.current;
    lastUnreadCount.current = nextCount;
    setUnreadCount(nextCount);
    setSupportUnreadCount(nextSupportCount);
    if (!unreadCountInitialized.current) {
      unreadCountInitialized.current = true;
      return;
    }
    if (nextCount > previousCount) {
      const delta = nextCount - previousCount;
      setNotice(delta === 1 ? "Nueva notificacion operativa. Revisa la campana." : `${delta} notificaciones operativas nuevas. Revisa la campana.`);
    }
  }, [setNotice]);

  const loadUnreadCount = useCallback(async () => {
    const startedAt = actionStartedAt();
    try {
      const payload = await getAdminNotificationsUnreadCount<{ unread_count: number; support_unread_count?: number }>(request);
      applyUnreadCount(payload.unread_count, payload.support_unread_count ?? 0);
      setUnreadCountState("ready");
    } catch (error) {
      setUnreadCountState("stale");
      recordActionFailed("admin_notifications_unread_refresh", "admin_notifications", startedAt, error instanceof Error ? error.name : undefined);
    }
  }, [applyUnreadCount, request]);

  const loadNotifications = useCallback(async (status = "unread") => {
    try {
      const payload = await listAdminNotifications<AdminNotificationsList>(request, status);
      setNotifications(payload.items);
      await loadUnreadCount();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos cargar notificaciones.");
    }
  }, [loadUnreadCount, request, setNotice]);

  const togglePanel = useCallback(async () => {
    const nextOpen = !panelOpen;
    setPanelOpen(nextOpen);
    if (nextOpen) {
      await loadNotifications("unread");
    }
  }, [loadNotifications, panelOpen]);

  const markRead = useCallback(async (notificationId: string) => {
    setNotificationBusyId(notificationId);
    try {
      await markAdminNotificationRead(request, notificationId);
      setNotifications((items) => items.map((item) => (item.id === notificationId ? { ...item, status: "read" } : item)));
      await loadUnreadCount();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos marcar como leida.");
    } finally {
      setNotificationBusyId(null);
    }
  }, [loadUnreadCount, request, setNotice]);

  const dismiss = useCallback(async (notificationId: string) => {
    if (!adminMutable) {
      setNotice("Solo admin/super_admin puede descartar notificaciones.");
      return;
    }
    setNotificationBusyId(notificationId);
    try {
      await dismissAdminNotification(request, notificationId);
      setNotifications((items) => items.filter((item) => item.id !== notificationId));
      await loadUnreadCount();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos descartar la notificacion.");
    } finally {
      setNotificationBusyId(null);
    }
  }, [adminMutable, loadUnreadCount, request, setNotice]);

  const resolve = useCallback(async (notificationId: string) => {
    if (!adminMutable) {
      setNotice("Solo admin/super_admin puede resolver notificaciones.");
      return;
    }
    setNotificationBusyId(notificationId);
    try {
      await resolveAdminNotification(request, notificationId);
      setNotifications((items) => items.filter((item) => item.id !== notificationId));
      await loadUnreadCount();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "No pudimos resolver la notificacion.");
    } finally {
      setNotificationBusyId(null);
    }
  }, [adminMutable, loadUnreadCount, request, setNotice]);

  const openNotification = useCallback(async (notification: AdminNotification) => {
    if (adminMutable) {
      await markRead(notification.id);
    }
    const target = routeTarget(notification);
    if (target.type === "business_intake" && target.id) {
      await handlers.openBusinessIntake(target.id);
      return;
    }
    if (target.type === "support_ticket" && target.id) {
      await handlers.openSupportTicket(target.id);
      return;
    }
    if (target.type === "order" && target.id) {
      await handlers.openOrder(target.id, target.highlightMessageId);
      return;
    }
    if (target.type === "credit_purchase") {
      await handlers.loadCreditPurchases("under_review");
      return;
    }
    if (target.type === "notification_job") {
      await handlers.loadJobs();
      return;
    }
    handlers.setView("dashboard");
  }, [adminMutable, handlers, markRead]);

  return {
    notifications,
    unreadCount,
    panelOpen,
    notificationBusyId,
    supportUnreadCount,
    unreadCountState,
    loadNotifications,
    loadUnreadCount,
    togglePanel,
    markRead,
    dismiss,
    resolve,
    openNotification
  };
}
